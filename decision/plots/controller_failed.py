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

# controlpdf = control / sum(control)
# failedpdf = failed / sum(failed)

# controlcdf = np.cumsum(controlpdf)
# failedcdf = np.cumsum(failedpdf)

fig = plt.figure()
ax = fig.add_subplot(1,1,1)
ax.plot(xvalues, controlcdf, label='No Failure')
ax.plot(xvalues2, failedcdf, label='Controller Failure')
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels)
ax.set_xlabel('Average Stream Performance')
ax.set_ylabel('% of trials')
plt.show()
