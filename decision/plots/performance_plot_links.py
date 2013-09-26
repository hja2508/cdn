#!/usr/bin/python

from  pylab import *
import matplotlib.pyplot as plt

c = open('central_avg_links').read().split('\n')[:-1]
c = [eval(l.split(':')[1]) for l in c]

s = open('static_avg_links').read().split('\n')[:-1]
s = [eval(l.split(':')[1]) for l in s]

LINKS = 2384
FRACT = 0.01

x = xrange(1,len(s)+1)
x = [int(j*FRACT*LINKS) for j in x]

fig = plt.figure()
ax = fig.add_subplot(1,1,1)
ax.plot(x,s, label='No Coordination (Local)')
ax.plot(x,c, label='Global Coordination (VDN)')
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels, loc='upper left')
ax.set_xlabel('Number of Links')
ax.set_ylabel('Average Video Channel Bitrate (Kbps)')
plt.show()
