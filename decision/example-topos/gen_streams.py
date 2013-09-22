#!/usr/bin/python

import random

random.seed()

for i in xrange(90):
    s = 'g_'+str(i+10)+'\t'+str(random.random())+'\t[200kbps, 400kbps, 800kbps]\t{'
    for j in xrange(30):
        s += 'n_'+str(random.randrange(0, 4000))+'='+str(random.random())+', '
    s = s[:-2]
    s += '}'
    print s

