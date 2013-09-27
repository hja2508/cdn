#!/usr/bin/python

from  pylab import *
import matplotlib.pyplot as plt
import datetime
from bisect import bisect_left

class discrete_cdf:
    def __init__(self, data):
        self._data = data # must be sorted
        self._data_len = float(len(data))

    def __call__(self, point):
        return (len(self._data[:bisect_left(self._data, point)]) / 
                self._data_len)

def smooth(xvs, cdf, i):
    b = []
    w = []
    xb = []
    xw = []
    for j,v in enumerate(cdf):
        if j % i == (i-1):
            w.append(sum(b)/len(b))
            xw.append(sum(xb)/len(xb))
            b = []
            xb = []
        b.append(v)
        xb.append(xvs[j])
    return xw, w

c = open('controller_failed_long_abbr').read().split('\n')[:-1]

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
control = [int(l) for l in control]
failed = sorted(failed)
failed = [int(l) for l in failed]

cdf = discrete_cdf(control)
xvalues = range(0, max(control))
controlcdf = [cdf(point) for point in xvalues]

cdf2 = discrete_cdf(failed)
xvalues2 = range(0, max(failed))
failedcdf = [cdf2(point) for point in xvalues2]

xvalues, controlcdf = smooth(xvalues, controlcdf, 3)
xvalues2, failedcdf = smooth(xvalues2, failedcdf, 3)
xvalues.append(xvalues[-1]+1)
controlcdf.append(1)
xvalues2.append(xvalues2[-1]+1)
failedcdf.append(1)


font = { 'size' : 20}
plt.rc('font', **font)

fig = plt.figure()
ax = fig.add_subplot(1,1,1)
fig.subplots_adjust(top=.95, bottom=.13, left=.15)
ax.plot(xvalues, controlcdf, label='No Failure', linewidth=5)
ax.plot(xvalues2, failedcdf, label='Controller Failure', linewidth=5, linestyle='--')
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels, loc="upper left")
ax.set_xlabel('Average Video Channel Performance (Kbps)')
ax.set_ylabel('% of trials (CDF)')
savefig('controller_failure.pdf')
#plt.show()
