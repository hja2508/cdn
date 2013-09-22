#!/usr/bin/python

from  pylab import *
import matplotlib.pyplot as plt
import datetime

c = open('central_timing').read().split('\n')[:-1]
c = [datetime.datetime.strptime(l, '%Y-%m-%d %X.%f') for l in c]
y = []
for i in xrange(1,len(c)):
    y.append((c[i]-c[i-1]).seconds)
print y

j = len(y)-1
y2 = []
for i in xrange(10):
    y2.append(y[j])
    j = int(j/2)

x = xrange(1,len(y2)+1)

fig = plt.figure()
ax = fig.add_subplot(1,1,1)
ax.plot(x,y2, label='Locally Optimal')
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels)
ax.set_xlabel('Number of Workers')
ax.set_ylabel('Decision Latency')
plt.show()
