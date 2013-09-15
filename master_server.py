#!/usr/bin/python

import rpyc, time, threading, sys, socket, thread, os, signal
from threading import Thread
from rpyc.utils.server import ThreadPoolServer
from plcommon import TimedThreadedDict, rpc, printtime, stime, check_output
from decision.decision import DecisionEngine
from subprocess import Popen, PIPE
import logging
logging.basicConfig()

RPC_PORT = 43278;
CLIENT_PORT = 3000
CHECK_PERIOD = 3
DECISION_PERIOD = 3
STATS_TIMEOUT = 3

HEARTBEATS = TimedThreadedDict() # hostname --> [color, lat, lon, [neighbor latlon]]
DSTATSD = {} # hostname --> {key: hostname, value: throughput}
LATLOND = {} # IP --> [lat, lon]
NAMES = [] # names
NAME_LOOKUP = {} # names --> hostname
HOSTNAME_LOOKUP = {} # hostname --> names
IP_LOOKUP = {} # IP --> hostname

FINISHED_EVENT = threading.Event()

CDN_DIR = '/home/cmu_xia/cdn/'
LOG_DIR = CDN_DIR + 'logs/'
DECISION_DIR = CDN_DIR + 'decision/'
DECISION_SCRIPT = DECISION_DIR + 'decision_engine.py'
STATS_FILE = LOG_DIR + 'stats.txt'
LATLON_FILE = CDN_DIR + 'IPLATLON'
NAMES_FILE = CDN_DIR + 'names'
NODE_TOPO_FILE = CDN_DIR + 'node_topo'

# note that killing local server is not in this one
STOP_CMD = '"sudo killall sh; sudo killall init.sh; sudo killall rsync; sudo /usr/sbin/httpd -k stop"'
KILL_LS = '"sudo killall -s INT local_server.py; sudo killall -s INT python; sleep 1; sudo killall local_server.py; sudo killall python"'
START_CMD = '"curl https://raw.github.com/mukerjee/cdn/master/init.sh > ./init.sh && chmod 755 ./init.sh && ./init.sh && python -u ~/cdn/local_server.py"'
SSH_CMD = 'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 cmu_xia@'

NODES = [[],[],[]] # hostname

MAX_LINK = 1000000

PRINT_VERB = [] # print verbosity
NODE_WATCHERS = {} # hostname -> [(NodeWatcher Thread, goOnEvent)]
NODE_WATCHERS_LOCK = thread.allocate_lock()

class NodeWatcher(threading.Thread):
    def preexec(self): # Don't forward signals.
        os.setpgrp()

    def __init__(self, host, goOnEvent, finishEvent):
        super(NodeWatcher, self).__init__()
        self.goOnEvent = goOnEvent
        self.finishEvent = finishEvent
        self.host = host
        self.out = open('/tmp/%s-log' % (self.host),'w',0)

    def __del__(self):
        self.out.close()

    def print_write(self, s):
        if self.host in PRINT_VERB: printtime('%s: %s' % (self.host, s))
        self.out.write('%s: %s\n' % (stime(), s))
        
    def std_listen(self, handle, out):
        while True:
            line = handle.readline()
            if not line:
                return
            if out: out.write('%s: %s' %(stime(), line))

    def hard_stop(self):
        self.ssh_run(STOP_CMD, checkRC=False)
        self.ssh_run(KILL_LS, checkRC=False)

    def ssh_run(self, cmd, checkRC=True, waitForCompletion=True):
        def target(p):
            p.wait()
            [t.join() for t in ts]

        self.print_write('launching subprocess: %s' % cmd)
        p = Popen(SSH_CMD+'%s %s' % (self.host, cmd), shell=True, stdout=PIPE, stderr=PIPE, preexec_fn = self.preexec)
        ts = [Thread(target=self.std_listen, args=(p.stdout, self.out))]
        ts += [Thread(target=self.std_listen, args=(p.stderr, self.out))]
        [t.start() for t in ts]
            
        t = Thread(target=target, args=(p, ))
        t.start()
        while waitForCompletion or self.goOnEvent.isSet():
            t.join(1)
            if not t.isAlive(): break
        if t.isAlive():
            os.kill(p.pid, signal.SIGTERM)
        self.print_write('finished running subprocess: %s' % cmd)
        if checkRC and self.goOnEvent.isSet():
            rc = p.returncode
            if rc is not 0:
                c = SSH_CMD+'%s %s' % (self.host, cmd)
                raise Exception("subprocess.CalledProcessError: Command '%s'" \
                                    "returned non-zero exit status %s" % (c, rc))

    def clearFinish(self):
        self.finishEvent.clear()

    def clearGoOn(self):
        self.goOnEvent.clear()

    def run(self):
        should_run = True
        while should_run:
            should_run = False
            self.print_write('launching...')
            self.hard_stop()
            try:
                self.ssh_run(START_CMD, waitForCompletion=False)
            except Exception, e:
                if self.finishEvent.isSet():
                    self.print_write('NW.run Exception: %s' % e)
                    try:
                        rpc('localhost', 'error', ('Startup', self.host))
                    except:
                        pass
#             if self.finishEvent.isSet() and self.host in BACKBONES:
#                 should_run = True
#                 self.goOnEvent.set()
        self.hard_stop()
        self.print_write('finished running process')
        NODE_WATCHERS.pop(self.host)


class MasterService(rpyc.Service):
    def on_connect(self):        
        self._host = IP_LOOKUP[self._conn._config['endpoints'][1][0]]
        self._conn._config['allow_pickle'] = True

    def on_disconnect(self):
        pass

    def exposed_get_nodes_to_check(self):
        if self._host in NODES[2]: #SOURCES
            return NODES[1] #REFLECTORS
        if self._host in NODES[1]: #REFLECTORS
            return NODES[0] #EDGES
        return []

    def exposed_should_cache(self):
        return True

    def exposed_heartbeat(self):
        lat, lon = LATLOND[socket.gethostbyname(self._host)]
        nlatlon = []
        if self._host in NODES[0]: #EDGES
            color = 'red'
        elif self._host in NODES[1]: #REFLECTORS
            color = 'blue'
        elif self._host in NODES[2]: #SOURCES
            color = 'green'
        HEARTBEATS[self._host] = [color, lat, lon]

    def exposed_discovery_stats(self, stats):
        if not self._host in DSTATSD:
            DSTATSD[self._host] = {}
        DSTATSD[self._host][stats[0]] = stats[1]
        if 'stats' in PRINT_VERB: printtime('%s\t %s' % (self._host, DSTATSD[self._host]))

    def exposed_error(self, msg, host):
        printtime('<<<< %s  (error (not doing anything about it)!): %s >>>>' % (host, msg))
#         host = self._host if host == None else host
            
    def exposed_hard_restart(self, host):
        NODE_WATCHERS_LOCK.acquire()
        if host in NODE_WATCHERS:
            NODE_WATCHERS[host].clearGoOn()
        else:
            goEv = threading.Event()
            goEv.set()
            finishEv = threading.Event()
            finishEv.set()
            nw = NodeWatcher(host=host, goOnEvent=goEv, finishEvent=finishEv)
            nw.start()
            NODE_WATCHERS[host] = nw
        NODE_WATCHERS_LOCK.release()

        
class Printer(threading.Thread):
    def buildMap(self, beats):
        url = 'http://maps.googleapis.com/maps/api/staticmap?center=Kansas&zoom=4&size=640x400&maptype=roadmap&sensor=false'
        for beat in beats:
            if beat[0] != 'red':
                url += '&markers=color:%s|%s,%s' % (beat[0],beat[2],beat[1])
            else:
                url += '&markers=%s,%s' % (beat[2],beat[1])
        html = '<html>\n<head>\n<title>Current Nodes In Topology</title>\n<meta http-equiv="refresh" content="60">\n</head>\n<body>\n<img src="%s">\n</body>\n</html>' % url
        return html

    def run(self):
        while FINISHED_EVENT.isSet():
            beats = HEARTBEATS.getClients()
            f = open('/var/www/html/map.html', 'w')
            f.write(self.buildMap(beats))
            f.close()

            time.sleep(CHECK_PERIOD)


class Decision(threading.Thread):
    def run(self):
        while FINISHED_EVENT.isSet():
            nodeMap = {}
            nodeRMap = {}
            for i,key in enumerate(HOSTNAME_LOOKUP):
                nodeMap[key] = i+1
                nodeRMap[i+1] = key

            sorted_E = []
            unsorted_RE = []

            temp = []
            for node in NODES[2]: #SOURCES
                link = (0, nodeMap[node], MAX_LINK)
                unsorted_RE += [link]
                temp += [link]
            sorted_E.append(temp)

            for key, value in DSTATSD.iteritems():
                temp = []
                for k, v in value.iteritems():
                    link = (nodeMap[key], nodeMap[k], v)
                    unsorted_RE += [link]
                    temp += [link]
                sorted_E.append(temp)

            G = [[2.0, [200, 400, 800], [(1, 1.0)]], 
                 [1.0, [100, 300, 900], [(1, 1.0)]]]

            print G
            print sorted_E
            print unsorted_RE

            req = {}
            if sorted_E:
                try:
                    req = DecisionEngine(G, sorted_E, unsorted_RE)
                except Exception, e:
                    print e

            print '<<<<<<REQ!!'
            for k,v in req.iteritems():
                for k2,v2 in v.iteritems():
                    v[k2] = [(nodeRMap[i[0]], i[1]) for i in v2]
            
            print req
        
            for node,i in nodeMap.iteritems():
                if req[i]:
                    print node
                    rpc(node, 'update_table', (req[i],))

            time.sleep(DECISION_PERIOD)


class Runner(threading.Thread):
    def run(self):
        for t in NODES:
            for node in t:
                while True:
                    try:
                        rpc('localhost', 'hard_restart', (node, ))
                        break;
                    except Exception, e:
                        printtime('%s' % e)
                        time.sleep(1)


if __name__ == '__main__':
    latlonfile = open(LATLON_FILE, 'r').read().split('\n')
    for ll in latlonfile:
        ll = ll.split(' ')
        LATLOND[ll[0]] = ll[1:-1]

    ns = open(NAMES_FILE,'r').read().split('\n')[:-1]
    NAMES = [n.split('#')[1].strip() for n in ns]
    nl = [line.split('#') for line in ns]
    NAME_LOOKUP = dict((n.strip(), host.strip()) for (host, n) in nl)
    HOSTNAME_LOOKUP = dict((host.strip(), n.strip()) for (host, n) in nl)

    topo_file = NODE_TOPO_FILE

    lines = open(topo_file,'r').read().split('\n')
    type = 0
    for line in lines:
        if line == "":
            type += 1
            continue
        NODES[type].append(NAME_LOOKUP[line])
    for t in NODES:
        for node in t:
            IP_LOOKUP[socket.gethostbyname(node)] = node

    IP_LOOKUP['127.0.0.1'] = socket.gethostbyaddr('127.0.0.1')

    PRINT_VERB.append('stats')
    PRINT_VERB.append('master')
    for t in NODES:
        [PRINT_VERB.append(node) for node in t]

    printtime(('Threaded heartbeat server listening on port %d\n' 
              'press Ctrl-C to stop\n') % RPC_PORT)

    FINISHED_EVENT.set()
    printer = Printer()
    printer.start()

    runner = Runner()
    runner.start()

    decision = Decision()
    decision.start()

    try:
        t = ThreadPoolServer(MasterService, port = RPC_PORT)
        t.start()
    except Exception, e:
        printtime('%s' % e)

    FINISHED_EVENT.clear()

    printtime('Master_Server killing all clients')
    for host in NODE_WATCHERS:
        NODE_WATCHERS[host].clearFinish()
        NODE_WATCHERS[host].clearGoOn()
    while len(NODE_WATCHERS): time.sleep(1)

    printtime('Exiting, please wait...')
    printer.join()
    runner.join()
    decision.join()

    printtime('Finished.')
    
    sys.exit(0)
