#!/usr/bin/python

import shlex, sys
from subprocess import Popen, PIPE
from os.path import splitext

total = 0
current = 1

def ssh_run(host, cmd):
    c = SSH_CMD + '%s %s' % (node, cmd)
    sys.stdout.write('(%s/%s) %s: ' % (current, total, node))
    sys.stdout.flush()
    process = Popen(shlex.split(c),stdout=PIPE,stderr=PIPE)
    out = process.communicate()
    sys.stdout.write('\r(%s/%s) %s: %s' % (current, total, node, out[0]))
    sys.stdout.flush()
    rc = process.wait()


if len(sys.argv) < 3:
    print 'usage %s [all_nodes] [init|uname]' % (sys.argv[0])
    sys.exit(-1)

nodes = open(sys.argv[1],'r').read().split('\n')
nodes = [node.split('#')[0].strip() for node in nodes]

#nodes = getoutput('ls /tmp/ | grep log').split('\n')
#nodes = [node.split('-log')[0].strip() for node in nodes]

SSH_CMD = 'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 cmu_xia@'
STOP_CMD = '"sudo killall sh; sudo killall init.sh; sudo killall rsync; sudo killall local_server.py; sudo killall python; sudo /usr/sbin/httpd -k stop"'
INIT = '"curl https://raw.github.com/XIA-Project/xia-core/develop/experiments/planetlab/init.sh > ./init.sh && chmod 755 ./init.sh && ./init.sh"'
UNAME = '"uname -r"'
LS = '"ls"'
RM = '"rm -rf ~/*; rm -rf ~/.*"'
INSTALL_APACHE = '"sudo yum -y install httpd"'

if sys.argv[2] == 'init':
    cmd = INIT
elif sys.argv[2] == 'uname':
    cmd = UNAME
elif sys.argv[2] == 'ls':
    cmd = LS
elif sys.argv[2] == 'rm':
    cmd = RM
elif sys.argv[2] == 'stop':
    cmd = STOP_CMD
elif sys.argv[2] == 'install-apache':
    cmd = INSTALL_APACHE

total = len(nodes)
print 'launching %s' % (cmd)
for node in nodes:
    try:
        ssh_run(node, cmd)
        current+=1;
    except:
        pass
