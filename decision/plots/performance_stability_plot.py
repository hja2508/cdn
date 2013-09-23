#!/usr/bin/python

from  pylab import *
import matplotlib.pyplot as plt

c = open('central_stab').read().split('\n')[:-1]
c = [eval(l) for l in c]

for i in xrange(len(c)): # each trial
    trial_diff = 0
    for node, dict in c[i].items(): # each node
        for group, paths in dict.items(): # each group
            dict[group] = {}
            for parent, br in paths:
                try:
                    dict[group][parent] += br
                except:
                    dict[group][parent] = br

#print c[0]

total = 0
for node, dict in c[0].items(): # each node
    for group, paths in dict.items(): # each group
        for parent, br in paths.items(): # each parent
            total += br

y = []
for i in xrange(len(c)): # each trial
    trial_diff = 0
    for node, dict in c[0].items(): # each node
        for group, paths in dict.items(): # each group
            for parent, br in paths.items():
                try:
                    trial_diff += br - c[i][node][group][parent]
                except:
                    trial_diff += br
    y.append(100*float(trial_diff)/total)

x = xrange(0,len(y))
x = [l*5 for l in x]

fig = plt.figure()
ax = fig.add_subplot(1,1,1)
ax.plot(x,y, label='Globally Optimal')
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels, loc='right')
ax.set_xlabel('Input Variance: % of inconsistent links/streams')
ax.set_ylabel('Decision Variance: % of forwarding tables changed')
plt.show()
