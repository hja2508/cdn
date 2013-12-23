#!/usr/bin/python
import sys

f = open(sys.argv[1], 'r')
f2 = open('avg_birate_' + sys.argv[1], 'w')
f3 = open('LPtime_' + sys.argv[1], 'w')

for l in f :
	if 'Average data rate of stream' in l :
		f2.write(l.split(': ')[1])
		#f2.write(l)
	elif 'AFTER' in l :
		f3.write(l.split(' ')[2])
		#f3.write(l)

f.close()
f2.close()
f3.close()

