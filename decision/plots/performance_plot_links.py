#!/usr/bin/python

from  pylab import *
import matplotlib.pyplot as plt
import numpy as np

def bin(c):
    b = []
    w = []
    e = []
    for i,l in enumerate(c):
        b.append(l)
        if i % 5 == 4:
            w.append(sum(b) / len(b))
            e.append(np.std(b))
            b = []
    return (w,e)

def fatcaps(caps):
    for cap in caps:
        cap.set_markeredgewidth(3)

c = open('central_avg_links').read().split('\n')[:-1]
c = [eval(l.split(':')[1]) for l in c]

s = open('static_avg_links').read().split('\n')[:-1]
s = [eval(l.split(':')[1]) for l in s]

(cw, ce) = bin(c)
(sw, se) = bin(s)

LINKS = 2384
FRACT = 0.01

x = xrange(1,len(sw)+1)
x = [int(j*FRACT*LINKS)*5 for j in x]

font = { 'size' : 20}
plt.rc('font', **font)

fig = plt.figure()
ax = fig.add_subplot(1,1,1)
fig.subplots_adjust(top=.95, bottom=.13, left=.15)
(_, caps, _) = ax.errorbar(x,cw, yerr=ce, linestyle='-', label='Global Coordination (VDN)', elinewidth=3, linewidth=5)
fatcaps(caps)
(_, caps, _) = ax.errorbar(x,sw, yerr=se, linestyle='--', label='No Coordination (Local)', elinewidth=3, linewidth=5)
fatcaps(caps)
handles, labels = ax.get_legend_handles_labels()
ylim([-10,700])
ax.legend(handles, labels, loc='upper left')
ax.set_xlabel('Number of Links')
ax.set_ylabel('Average Video Channel Bitrate (Kbps)')
savefig('performance_links.pdf')
#plt.show()
