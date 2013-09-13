#!/usr/bin/python

from  pylab import *
import matplotlib.pyplot as plt

n = open('scatter_array').read().split('\n')
b = eval(n[0])
b = [x/1000.0 for x in b]
w = eval(n[1])
w = [x[0] for x in w]

print b
print w

fig = plt.figure()
ax = fig.add_subplot(1,1,1)
fig.subplots_adjust(bottom=0.17)
ax.set_xscale('log')
plt.scatter(w,b)
plt.xlim([-1,1])
matplotlib.rcParams.update({'font.size': 26})
ax.set_xlabel('Stream Weight')
ax.set_ylabel('Total Received Bitrate (Mbps)')
plt.show()
