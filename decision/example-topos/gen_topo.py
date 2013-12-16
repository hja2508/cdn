#!/usr/bin/python

import random

random.seed()

NODES = 1000
bf = int(.1 * NODES)
SOURCE = xrange(1,2*bf)
REFLECTOR = xrange(2*bf,5*bf)
EDGE = xrange(5*bf,NODES)
GROUPS = 10
NODES_PER_GROUP = 20
PROB_OF_LINK = .01

s = 'Node:\n'
l = 0

def add_link(i,j,skip_prob=False):
    global s, l
    if skip_prob or random.random() < PROB_OF_LINK:
        s += 'l_%d\t%f\tn_%d\tn_%d\n' % \
            (l, float(random.randrange(100, 2000, 100)), i, j)
        l += 1


for i in xrange(NODES):
    s += 'n_' + str(i) + '\n'

s += 'Link:\n'
for i in xrange(NODES):
    if i in [0]:
        for j in SOURCE:
            add_link(i,j, True)
    if i in SOURCE:
        for j in REFLECTOR:
            add_link(i,j)
    if i in REFLECTOR:
        for j in EDGE:
            add_link(i,j)

s += 'Groups:\n'
g = 0
for i in xrange(GROUPS):
    s += 'g_%d\t%f\t[200kbps, 400kbps, 800kbps]\t{' % (i, 1.0)
    for j in xrange(NODES_PER_GROUP):
        s += 'n_%d=%f, ' % (random.sample(EDGE,1)[0], 1.0)
    s = s[:-2] + '}\n'

print s
