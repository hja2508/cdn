#!/usr/bin/python

import rpyc, threading, time
from plcommon import check_output, rpc, printtime
from rpyc.utils.server import ThreadPoolServer

RPC_PORT = 43278
MASTER_SERVER = 'GS11698.SP.CS.CMU.EDU'
#'ec2-54-200-36-219.us-west-2.compute.amazonaws.com' 

BEAT_PERIOD = 3
DISCOVERY_PERIOD = 3
HTTP_PORT = 8881

CDN_DIR = '/home/cmu_xia/cdn/'
HTTPD_CONF_TOP = CDN_DIR + 'httpd.conf.top'
HTTPD_CONF_CACHE = CDN_DIR + 'httpd.conf.cache'
HTTPD_TEMP = CDN_DIR + 'httpd.conf.temp'
HTTPD_CONF = '/etc/httpd/conf/httpd.conf'

HTTP_START = 'sudo /usr/sbin/httpd -k graceful'

my_name = check_output("hostname")[0].strip()

#ForwardingTable = {}

FINISH_EVENT = threading.Event()    
    
def wait_for_neighbor(neighbor):
    while True:
        try:
            printtime('waiting on: %s' % neighbor)
            out = rpc(neighbor, 'check_httpd', ())
            return out
        except:
            time.sleep(1)

def start_httpd(conf_file = HTTPD_CONF_TOP):
    printtime('Starting httpd')
    check_output('sudo cp %s %s' % (conf_file, HTTPD_CONF))
    check_output(HTTP_START)


class MyService(rpyc.Service):
    def on_connect(self):
        self._conn._config['allow_pickle'] = True

    def on_disconnect(self):
        pass

    
    def exposed_check_httpd(self):
        check_output('pgrep httpd', False)
            
    def exposed_run_commands(self):
        printtime('requesting commands!')
        commands = rpc(MASTER_SERVER, 'get_commands', ())
        printtime('commands received!')
        printtime('commands: %s' % commands)
        for command in commands:
            printtime(command)
            exec(command)

    def exposed_update_table(self, new_table):
        #ForwardingTable = new_table
        #if not new_table:
        #    return
        s = open(HTTPD_CONF_TOP).read()
        if rpc(MASTER_SERVER, 'should_cache', ()):
            s += open(HTTPD_CONF_CACHE).read()
        for k in new_table:
            v = new_table[k]
            s += '<Proxy balancer://%d>\n' % (k)
            for t in v:
                s += 'BalancerMember http://%s:%d/ loadfactor=1\n' % (t[0], HTTP_PORT)
            s += 'ProxySet lbmethod=bytraffic\n'
            s += '</Proxy>\n'
            s += 'ProxyPass /%d/ balancer://%d\n' % (k, k)
        f = open(HTTPD_TEMP, "w")
        f.write(s)
        f.close()
        start_httpd(HTTPD_TEMP)


class Mapper(threading.Thread):
    def run(self):
        while FINISH_EVENT.isSet():
            try:
                rpc(MASTER_SERVER, 'heartbeat', ())
            except Exception, e:
                pass
            time.sleep(BEAT_PERIOD)

class Discovery(threading.Thread):
    def run(self):
        while FINISH_EVENT.isSet():
            try:
                printtime('<<<<DISCOVERY>>>>')
                nodes_to_check = rpc(MASTER_SERVER, 'get_nodes_to_check', ())
                for node in nodes_to_check:
                    wait_for_neighbor(node)
                    cmd = 'ab http://%s:%d/test | grep "Transfer rate"' % (node, HTTP_PORT)
                    out = check_output(cmd)[0]
                    printtime(out)
                    stats = (node, int(float(out.split(':')[1].split('[')[0].strip())))
                    rpc(MASTER_SERVER, 'discovery_stats', (stats,))
            except Exception, e:
                print e
                pass
            time.sleep(DISCOVERY_PERIOD)


if __name__ == '__main__':
    printtime(('RPC server listening on port %d\n'
        'press Ctrl-C to stop\n') % RPC_PORT)

    FINISH_EVENT.set()
    mapper = Mapper()
    mapper.start()

    discovery = Discovery()
    discovery.start()

    start_httpd()

    try:
        t = ThreadPoolServer(MyService, port = RPC_PORT)
        t.start()
    except Exception, e:
        printtime('%s' % e)

    printtime('Local_Server Exiting, please wait...')
    FINISH_EVENT.clear()
    mapper.join()
    discovery.join()

    runner.join()

    printtime('Local_Server Finished.')
