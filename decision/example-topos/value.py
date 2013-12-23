#!/usr/bin/python

import sys

if len(sys.argv) < 3 :
	print 'usage :', "./value.py n1000_50_2 [errors]"
	sys.exit()
	
f = open(sys.argv[1], "r")
l = sys.argv[2]
l = l.strip('[]')
lout = []
l = l.split('(')
l.pop(0)
d = {}
dout = {}

for i in l :
	temp = i.strip(')').split(',')
	lout.append((temp[0].strip("'"), int(temp[1].strip(')'))))

for i in lout :
	temp = i[0].split('_')
	if int(temp[1]) in d :
		d[int(temp[1])] += [int(temp[0][1:])] 
	else :
		d[int(temp[1])] = [int(temp[0][1:])]

for i in d :
	d[i].sort() 
#print d

for i in f :
	if "Groups" in i :
		break
for i in f :
	for di in d :
		if "g_" + str(di) in i :
			temp = i.split('\t')
			temp = temp[3].strip('{}')
			temp = temp.split(', ')
			print di,
			for j in d[di] :
				print temp[j],
	print ''
