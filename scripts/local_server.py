#!/usr/bin/python

import rpyc, threading, time
from plcommon import check_output, rpc, printtime
from rpyc.utils.server import ThreadPoolServer

RPC_PORT = 43278
MASTER_SERVER = 'GS11698.SP.CS.CMU.EDU'
BEAT_PERIOD = 3

my_name = check_output("hostname")[0].strip()

FINISH_EVENT = threading.Event()    
    
class MyService(rpyc.Service):
    def on_connect(self):
        self._conn._config['allow_pickle'] = True

    def on_disconnect(self):
        pass

    def exposed_get_hello(self):
        return 'hello'

    def exposed_gather_stats(self):
        printtime('<<<<GATHER STATS>>>>')

    def exposed_run_commands(self):
        printtime('requesting commands!')
        commands = rpc(MASTER_SERVER, 'get_commands', ())
        printtime('commands received!')
        printtime('commands: %s' % commands)
        for command in commands:
            printtime(command)
            exec(command)

    def exposed_wait_for_neighbors(self, neighbors, msg):
        while True:
            for neighbor in neighbors:
                try:
                    printtime('waiting on: %s' % neighbor)
                    out = rpc(neighbor, 'get_hello', ())
                    return out
                except:
                    printtime(msg)
                    time.sleep(1)

class Mapper(threading.Thread):
    def __init__(self, goOnEvent):
        super(Mapper, self).__init__()
        self.goOnEvent = goOnEvent

    def run(self):
        while self.goOnEvent.isSet():
            try:
                rpc(MASTER_SERVER, 'heartbeat', (my_name,))
            except Exception, e:
                pass
            time.sleep(BEAT_PERIOD)


class Runner(threading.Thread):
    def run(self):
        while FINISH_EVENT.isSet():
            try:
                rpc('localhost', 'run_commands', ())
                break
            except Exception, e:
                printtime('%s' % e)
                time.sleep(1)

if __name__ == '__main__':
    printtime(('RPC server listening on port %d\n'
        'press Ctrl-C to stop\n') % RPC_PORT)

    FINISH_EVENT.set()
    mapper = Mapper(goOnEvent = FINISH_EVENT)
    mapper.start()

    runner = Runner()
    runner.start()

    try:
        t = ThreadPoolServer(MyService, port = RPC_PORT)
        t.start()
    except Exception, e:
        printtime('%s' % e)

    printtime('Local_Server Exiting, please wait...')
    FINISH_EVENT.clear()
    mapper.join()

    runner.join()

    printtime('Local_Server Finished.')
