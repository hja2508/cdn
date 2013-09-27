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

def avg_dp(ctimer):
    i = 0
    ct = [0] * 30
    for v in ctimer:
        w = [item for sublist in v for item in sublist]
        if len(w) == 30:
            ct = [sum(t) for t in zip(ct, w)]
            i += 1
    ct = [l/i for l in ct]
    return ct


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

# print ctimer[-1]
# print ckilled

# print stimer[-1]
# print skilled

# print stimer

cxvalues, ckilledcdf = cdf(ckilled)
sxvalues, skilledcdf = cdf(skilled)

# s = open('static_avg').read().split('\n')[:-1]
# s = [eval(l.split(':')[1]) for l in s]

# s = s[:len(c)]
ct = avg_dp(ctimer)
#ct = [item for sublist in ctimer[-3] for item in sublist]
cx = xrange(1,len(ct)+1)

st = avg_dp(stimer)
#st = [item for sublist in stimer[-3] for item in sublist]
sx = xrange(1,len(st)+1)

sxvalues, skilledcdf = smooth(sxvalues, skilledcdf, 20)
cxvalues, ckilledcdf = smooth(cxvalues, ckilledcdf, 20)
sxvalues.append(sxvalues[-1]+1)
skilledcdf.append(1)
cxvalues.append(cxvalues[-1]+1)
ckilledcdf.append(1)

font = { 'size' : 20 }
plt.rc('font', **font)
#plt.rc('legend.fontsize', **20)

params = {'legend.fontsize': 16,
          'legend.linewidth': 2}
plt.rcParams.update(params)
#plt.legend(loc=2,prop={'size':6})

fig = plt.figure()
ax = fig.add_subplot(1,1,1)
fig.subplots_adjust(top=.95, bottom=.13, left=.15)
ax.plot(cx,ct, label='Partially Centralized (VDN)', linewidth=5)
ax.plot(sx,st, label='Purely Local', linewidth=5, linestyle='--')
ax.errorbar([5],[1250], xerr=[4.8], color='black', linewidth=3)
ax.errorbar([12],[1250], xerr=[1.8], color='black', linewidth=3)
ax.errorbar([22],[1250], xerr=[7.8], color='black', linewidth=3)
ax.annotate('Global', xy=(5,1300), xytext=(3, 1300))
ax.annotate('Local', xy=(5,1300), xytext=(10.2, 1300))
ax.annotate('Global', xy=(5,1300), xytext=(20, 1300))
ax.annotate('Link Failure', xy=(9.5,1100), xytext=(1,890),
            arrowprops=dict(facecolor='black',shrink=0.05),)
ax.annotate('Link Failure', xy=(9.5,800), xytext=(1,890),
            arrowprops=dict(facecolor='black',shrink=0.05),)
ax.annotate('Link Repair', xy=(20,780), xytext=(21.5,380),
            arrowprops=dict(facecolor='black',shrink=0.05),)
ax.annotate('Link Repair', xy=(20.5,420), xytext=(21.5,380),
            arrowprops=dict(facecolor='black',shrink=0.05),)
ylim([0, 1400])
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels, loc='lower right')
ax.set_xlabel('Time (seconds)')
ax.set_ylabel('Average Video Channel Bitrate (Kbps)')
savefig('data_plane_failure.pdf')
#plt.show()


fig = plt.figure()
ax = fig.add_subplot(1,1,1)
fig.subplots_adjust(top=.95, bottom=.13, left=.15)
ax.plot(cxvalues,ckilledcdf, label='Partially Centralized (VDN)', linewidth=5)
ax.plot(sxvalues,skilledcdf, label='Purely Local', linewidth=5, linestyle='--')
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels, loc="lower right")
ax.set_ylabel('% of trials (CDF)')
ax.set_xlabel('Performance during Convergence Phase')
savefig('data_plane_convergence_cdf.pdf')
#plt.show()
