#!/usr/bin/python

import random

GROUPS = 10
EDGE = xrange(9, 21)
NODES_PER_GROUP = 2

random.seed()

s = str()
for i in xrange(GROUPS):
    s += 'g_%d\t%f\t[200kbps, 400kbps, 800kbps]\t{' % (i, 1.0)
    r = random.sample(EDGE,NODES_PER_GROUP)
    for j in xrange(NODES_PER_GROUP):
        s += 'n_%d=%f, ' % (r[j], 1.0)
    s = s[:-2] + '}\n'
s = s[:-1]
print s

