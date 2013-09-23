#!/usr/bin/python

from  pylab import *
import matplotlib.pyplot as plt

c = open('central_avg').read().split('\n')[:-1]
c = [eval(l.split(':')[1]) for l in c]

s = open('static_avg').read().split('\n')[:-1]
s = [eval(l.split(':')[1]) for l in s]

s = s[:len(c)]
x = xrange(1,len(c)+1)

fig = plt.figure()
ax = fig.add_subplot(1,1,1)
ax.plot(x,s, label='Locally Optimal')
ax.plot(x,c, label='Globally Optimal')
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels)
ax.set_xlabel('Number of Unique Streams')
ax.set_ylabel('Average Stream Bitrate (Kbps)')
plt.show()