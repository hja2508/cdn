#!/usr/bin/python

from  pylab import *
import matplotlib.pyplot as plt
import datetime

c = open('scalability_rt').read().split('\n')[:-1]

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
ax.plot(x,time, label='Globally Optimal')
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels)
ax.set_xlabel('Number of Workers')
ax.set_ylabel('Decision Latency')
#plt.show()

fig = plt.figure()
ax = fig.add_subplot(1,1,1)
ax.plot(x,avg, label='Globally Optimal')
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels)
ax.set_xlabel('Number of Workers')
ax.set_ylabel('Average Stream Bitrate')
plt.show()
