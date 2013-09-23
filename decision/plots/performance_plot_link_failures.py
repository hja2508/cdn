#!/usr/bin/python

from  pylab import *
import matplotlib.pyplot as plt

c = open('central_avg_links').read().split('\n')[:-1]
c = [eval(l.split(':')[1]) for l in c]

s = open('static_avg_links').read().split('\n')[:-1]
s = [eval(l.split(':')[1]) for l in s]

c2 = []
s2 = []
for i in xrange(len(s)):
    c2.append(c[len(c)-1-i])
    s2.append(s[len(s)-1-i])
x = xrange(1,len(s)+1)

fig = plt.figure()
ax = fig.add_subplot(1,1,1)
ax.plot(x,s2, label='Locally Optimal')
ax.plot(x,c2, label='Globally Optimal')
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels)
ax.set_xlabel('% of Links Failed')
ax.set_ylabel('Average Stream Bitrate (Kbps)')
plt.show()
