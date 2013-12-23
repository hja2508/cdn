#!/usr/bin/python
import sys
import random

f = open(sys.argv[1], "r")
f2 = open("/home/carnival/cdn/decision/example-topos/numnodesgroups/2/cap100000/" + sys.argv[1] + "_capinc", "w")

for l in f :
	if "Link" in l :
		f2.write(l)
		break
	f2.write(l)
for l in f :
	if "Groups" in l :
		f2.write(l)
		break
	parse = l.split('\t')
	#parse[1] = str(float(parse[1]) + 1000)
	parse[1] = str(float(random.randrange(100, 100000, 100)))
	f2.write('\t'.join(parse))

for l in f :
	f2.write(l)

f.close()
f2.close()

	
