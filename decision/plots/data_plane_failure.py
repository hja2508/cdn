#!/usr/bin/python

from  pylab import *
import matplotlib.pyplot as plt

from bisect import bisect_left

class discrete_cdf:
    def __init__(self, data):
        self._data = data # must be sorted
        self._data_len = float(len(data))

    def __call__(self, point):
        return (len(self._data[:bisect_left(self._data, point)]) / 
                self._data_len)



def calc(c):
    j = 0
    timer = []
    killed = []
    fixed = []
    for i,v in enumerate(c):
        if v == "DATAKILLER (killing link)":
            timer.append([c[j:i]])
            if len(timer) > 1:
                timer[-2].append(c[j:i])
            j = i+1
        elif v == "DATAKILLER (fixing link)":
            timer[-1].append(c[j:i])
            j = i+2

    for t in timer:
        if len(t) != 3:
            timer.remove(t)
        for k,i in enumerate(t):
            t[k] = [eval(l.split(':')[1].split('time')[0]) for l in i]

    timer2 = []
    for i,t in enumerate(timer):
        if not(sum(t[0]) == 0 or sum(t[1]) == 0 or sum(t[2]) == 0):
            timer2.append(t)

    for t in timer2:
        for i, l in enumerate(t):
            if i % 2 == 0:
                fixed += [int(w) for w in l]
            else:
                killed += [int(w) for w in l]
    return (timer2, killed, fixed)


def cdf(killed):
    killed = sorted(killed)
    cdf = discrete_cdf(killed)
    xvalues = range(0, max(killed))
    killedcdf = [cdf(point) for point in xvalues]
    return (xvalues, killedcdf)

c = open('data_plane_failure_test_abbr').read().split('\n')[:-1]
s = open('data_plane_failure_test2_abbr').read().split('\n')[:-1] 

ctimer, ckilled, cfixed = calc(c)
stimer, skilled, sfixed = calc(s)

print ctimer[-1]
print ckilled

print stimer[-1]
print skilled

print stimer

cxvalues, ckilledcdf = cdf(ckilled)
sxvalues, skilledcdf = cdf(skilled)

# s = open('static_avg').read().split('\n')[:-1]
# s = [eval(l.split(':')[1]) for l in s]

# s = s[:len(c)]
ct = [item for sublist in ctimer[-2] for item in sublist]
cx = xrange(1,len(ct)+1)

st = [item for sublist in stimer[-2] for item in sublist]
sx = xrange(1,len(st)+1)

fig = plt.figure()
ax = fig.add_subplot(1,1,1)
ax.plot(sx,st, label='Purely Local')
ax.plot(cx,ct, label='Partially Centralized')
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels)
ax.set_xlabel('Time (seconds)')
ax.set_ylabel('Average Video Channel Bitrate (Kbps)')
plt.show()


fig = plt.figure()
ax = fig.add_subplot(1,1,1)
ax.plot(sxvalues,skilledcdf, label='Purely Local')
ax.plot(cxvalues,ckilledcdf, label='Partially Centralized')
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels)
ax.set_xlabel('% of Experiments (CDF)')
ax.set_ylabel('Performance Degradation during Convergence Phase')
plt.show()
