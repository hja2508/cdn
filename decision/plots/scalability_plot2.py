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

fig = plt.figure()
ax = fig.add_subplot(1,1,1)
ax.plot(x,time, label='Global Coordination(VDN)')
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels)
ax.set_xlabel('Number of Controllers')
ax.set_ylabel('Decision Latency (seconds)')
plt.show()

fig = plt.figure()
ax = fig.add_subplot(1,1,1)
ax.plot(x,avg, label='Global Coordination (VDN)')
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels)
ax.set_xlabel('Number of Controllers')
ax.set_ylabel('Average Video Channel Bitrate (Kbps)')
plt.show()
