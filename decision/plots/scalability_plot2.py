#!/usr/bin/python

from  pylab import *
import matplotlib.pyplot as plt
import datetime

c = open('scalability_justlpt_rt').read().split('\n')[:-1]

time = []
avg = []
for i in xrange(len(c)):
    l = eval(c[i].split(':')[1])
    if i%2 == 0:
        time.append(l)
    else:
        avg.append(l)

x = xrange(1,len(time)+1)

font = { 'size' : 20}
plt.rc('font', **font)

fig = plt.figure()
ax = fig.add_subplot(1,1,1)
fig.subplots_adjust(top=.95, bottom=.13, left=.15)
ax.plot(x,time, label='Global Coordination(VDN)', linewidth=5)
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels)
ax.set_xlabel('Number of Controllers')
ax.set_ylabel('Decision Latency (seconds)')
savefig('scalability2.pdf')
#plt.show()

fig = plt.figure()
ax = fig.add_subplot(1,1,1)
fig.subplots_adjust(top=.95, bottom=.13, left=.15)
ax.plot(x,avg, label='Global Coordination (VDN)', linewidth=5)
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels)
ax.set_xlabel('Number of Controllers')
ax.set_ylabel('Average Video Channel Bitrate (Kbps)')
savefig('scalability_performance.pdf')
#plt.show()
