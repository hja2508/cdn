#!/usr/bin/python

from  pylab import *
import matplotlib.pyplot as plt
import datetime

c = open('controller_failed_abbr').read().split('\n')[:-1]

control = []
failed = []
for i in xrange(len(c)):
    l = eval(c[i].split(':')[1])
    if i%2 == 0:
        control.append(l)
    else:
        failed.append(l)

control = [l for l in control if l != 0]
failed = [l for l in failed if l != 0]

control = sorted(control)
failed = sorted(failed)

controlcdf = [control[0]]
for i in xrange(1,len(control)):
    controlcdf.append(controlcdf[i-1] + control[i])

failedcdf = [failed[0]]
for i in xrange(1,len(failed)):
    failedcdf.append(failedcdf[i-1] + failed[i])

y1 = xrange(1,len(controlcdf)+1)
y1 = [100*float(y)/len(controlcdf) for y in y1]
y2 = xrange(1,len(failedcdf)+1)
y2 = [100*float(y)/len(failedcdf) for y in y2]

fig = plt.figure()
ax = fig.add_subplot(1,1,1)
ax.plot(controlcdf, y1, label='No Failure')
ax.plot(failedcdf, y2, label='Controller Failure')
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels)
ax.set_xlabel('Average Stream Performance')
ax.set_ylabel('% of trials')
plt.show()
