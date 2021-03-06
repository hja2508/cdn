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


c = open('central_avg').read().split('\n')[:-1]
c = [eval(l.split(':')[1]) for l in c]

s = open('static_avg').read().split('\n')[:-1]
s = [eval(l.split(':')[1]) for l in s]

(cw, ce) = bin(c)
(sw, se) = bin(s)

sw = sw[:len(cw)]
se = sw[:len(cw)]
x = xrange(1,len(cw)+1)
x = [l*5 for l in x]


font = { 'size' : 28}
plt.rc('font', **font)
params = {'legend.fontsize': 20,
          'legend.linewidth': 2}
plt.rcParams.update(params)

fig = plt.figure()
ax = fig.add_subplot(1,1,1)
fig.subplots_adjust(top=.95, bottom=.16, left=.20)
(_, caps, _) = ax.errorbar(x,cw, yerr=ce, linestyle='-', label='Global Coordination (VDN)', elinewidth=3, linewidth=7)
fatcaps(caps)
(_, caps, _) = ax.errorbar(x,sw, yerr=se, linestyle='--', label='No Coordination (Local)', elinewidth=3, linewidth=7)
fatcaps(caps)
handles, labels = ax.get_legend_handles_labels()
ylim([0,1500])
ax.legend(handles, labels)
ax.set_xlabel('Number of Video Channels')
ax.set_ylabel('Average Bitrate (Kbps)')
savefig('performance_streams.pdf')
#plt.show()
