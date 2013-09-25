#!/usr/bin/python

import rpyc, time, threading, sys, socket, thread, os, signal, random, string, copy
from threading import Thread
from rpyc.utils.server import ThreadPoolServer
from plcommon import TimedThreadedDict, rpc, printtime, stime, check_output
from decision.decision import DecisionEngine
from subprocess import Popen, PIPE
from pulp import *
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
TOTAL_STREAMS = 10
STREAM_CHANCE = .30

PRINT_VERB = [] # print verbosity
NODE_WATCHERS = {} # hostname -> [(NodeWatcher Thread, goOnEvent)]
NODE_WATCHERS_LOCK = thread.allocate_lock()

SOURCES = 0
REFLECTORS = 1
EDGES = 2

REQ = {}
ST = []
F = []
E = []
DECISION_RUNNING = True
DE_FLOPPER = 3
DE_FLOP_COUNT = 0

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

    def exposed_shut_off_DE(self):
        global DECISION_RUNNING
        DECISION_RUNNING = False

    def exposed_turn_on_DE(self):
        global DECISION_RUNNING
        DECISION_RUNNING = True

    def exposed_get_nodes_to_check(self):
        if self._host in NODES[SOURCES]: #SOURCES
            return NODES[REFLECTORS] #REFLECTORS
        if self._host in NODES[REFLECTORS]: #REFLECTORS
            return NODES[EDGES] #EDGES
        return []

    def exposed_should_cache(self):
        return True

    def exposed_heartbeat(self):
        lat, lon = LATLOND[socket.gethostbyname(self._host)]
        nlatlon = []
        if self._host in NODES[EDGES]: #EDGES
            color = 'red'
        elif self._host in NODES[REFLECTORS]: #REFLECTORS
            color = 'blue'
        elif self._host in NODES[SOURCES]: #SOURCES
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
        global REQ, ST, F, E, DE_FLOPPER, DE_FLOP_COUNT
        while FINISHED_EVENT.isSet():
            nodeMap = {}
            nodeRMap = {}
            for i,key in enumerate(HOSTNAME_LOOKUP):
                nodeMap[key] = i+1
                nodeRMap[i+1] = key
            nodeRMap[0] = 'dummy'

            sorted_E = {}




#             if len(DSTATSD) == 0:
#                 DSTATSD['planetlab1.cs.ucla.edu'] = {}
#                 DSTATSD['planetlab1.cs.ucla.edu']['planetslug4.cse.ucsc.edu'] = 1500
#                 DSTATSD['planetlab1.cs.ucla.edu']['planetlab01.cs.washington.edu'] = 1500
                
#                 DSTATSD['planetslug4.cse.ucsc.edu'] = {}
#                 DSTATSD['planetslug4.cse.ucsc.edu']['planetlab2.cs.colorado.edu'] = 1000

#                 DSTATSD['planetlab01.cs.washington.edu'] = {}
#                 DSTATSD['planetlab01.cs.washington.edu']['planetlab2.cs.colorado.edu'] = 1000



            for node in NODES[SOURCES]: #SOURCES
                link = (0, nodeMap[node], MAX_LINK)
                try:
                    sorted_E[0] += [link]
                except:
                    sorted_E[0] = [link]

            for key, value in DSTATSD.iteritems():
                for k, v in value.iteritems():
                    link = (nodeMap[key], nodeMap[k], v)
                    try:
                        sorted_E[nodeMap[key]] += [link]
                    except:
                        sorted_E[nodeMap[key]] = [link]

            G = []
            gs = open('streams').read().split('\n')[:-1]
            for g in gs:
                l = g.split('\t')
                br = l[2].translate(string.maketrans("","",), '{}[]kbps').strip().split(',')
                br = [eval(b) for b in br]
                T = l[3].translate(string.maketrans("","",), '{}[]').strip().split(',')
                T = [(eval(t.split('=')[0].split('_')[1]), eval(t.split('=')[1])) for t in T]
                G.append([eval(l[1]), br, T])

#             for i in xrange(TOTAL_STREAMS):
#                 terms = []
#                 for node in NODES[EDGES]: #edges
#                     if random.random() < STREAM_CHANCE:
#                         termweight = round(10*random.random(), 0)
#                         terms += [(nodeMap[node], termweight)]
#                 weight = round(10*random.random(), 0)
#                 kbps = [round(100*x, -2) for x in random.sample(xrange(25), 3)]
#                 kbps = sorted(kbps)
#                 if terms:
#                     G += [[weight, kbps, terms]]

            

            print G
            print sorted_E

            if sorted_E:
                try:
                    if DECISION_RUNNING:
                        REQ, ST, F, E = DecisionEngine(G, sorted_E, False)
                        print "RAN DECISION ENGINE"
                except Exception, e:
                    print e

            print REQ
            print ST
            print F
            print E
            
            aggr_br = {}
            stream_count = {}
            for node, dict in REQ.items():
                aggr_br[node] = {}
                stream_count[node] = {}
                for g, d in dict.items():
                    for link in d:
                        try:
                            aggr_br[node][link[0]] += link[1]
                            stream_count[node][link[0]] += 1
                        except:
                            aggr_br[node][link[0]] = link[1]
                            stream_count[node][link[0]] = 1

            reverse_edge = {}
            for node, es in sorted_E.items():
                for e in es:
                    try:
                        reverse_edge[e[1]].append(e)
                    except:
                        reverse_edge[e[1]] = [e]


                        
            for i,e in enumerate(E):
                if e[0] == 0 or e[1] == 0: continue
                new_lc = DSTATSD[nodeRMap[e[0]]][nodeRMap[e[1]]]
                E[i] = (e[0], e[1], new_lc)

            oavg = 0
            for g,v in enumerate(ST):
                for p,s in enumerate(v): # a single ST
                    if pulp.value(F[g][p]) == 0: continue
                    avg = 0
                    obn = MAX_LINK
                    for t in G[g][2]:
                        bn = MAX_LINK
                        for i in xrange(len(s)):
                            if s[i]:
                                e = E[i]
                                if e in reverse_edge[t[0]]:
                                    for k, r in enumerate(REQ[t[0]][g]):
                                        if r[0] == e[0]:
                                            rbr = pulp.value(F[g][p]) #r[1]
                                            lc = e[2]
                                            sc = stream_count[t[0]][e[0]]
                                            abr = aggr_br[t[0]][e[0]]
                                            if abr > lc:
                                                rbr = rbr - ((abr - lc)/sc)
                                                REQ[t[0]][g][k] = (r[0], rbr)
                                            bn = min(bn, rbr)
                                bn = min(bn, e[2])
                                for k, r in enumerate(REQ[t[0]][g]):
                                    if r[0] == e[0]:
                                        REQ[t[0]][g][k] = (r[0], bn)
                        avg += bn*(1.0/len(G[g][2]))
                        obn = min(obn, bn)
                    for i,e in enumerate(E):
                        if s[i]:
                            E[i] = (e[0], e[1], e[2] - obn)
                    oavg += avg*(1.0/len(G))
            print 'OAVG = ' + str(oavg)

            print '<<<<<<REQ!!'
            print REQ
            req2 = copy.deepcopy(REQ)
            for k,v in req2.iteritems():
                for k2,v2 in v.iteritems():
                    v[k2] = [(nodeRMap[i[0]], i[1]) for i in v2]
            
            print req2
        
            for node,i in nodeMap.iteritems():
                if i in req2 and req2[i]:
                    print node
                    try:
                        rpc(node, 'update_table', (req2[i],))
                    except:
                        pass

            DE_FLOPPER -= 1
            if DE_FLOPPER == 0:
                rpc('localhost', 'shut_off_DE', ())
                print 'CONTROLCRASHER (on): ' + str(oavg)
            elif DE_FLOPPER == -3:
                print 'CONTROLCRASHER (off): ' + str(oavg)
                DE_FLOP_COUNT += 1
                print 'DE_FLOP COUNT: ' + str(DE_FLOP_COUNT)
                DE_FLOPPER = 3
                rpc('localhost', 'turn_on_DE', ())

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
    random.seed()

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
