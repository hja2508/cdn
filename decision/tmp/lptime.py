#!/usr/bin/python

f = open('lptime', 'r')
f2 = open('onlylptime', 'w')

for l in f :
	if 'LPtime' in l :
		f2.write(l.strip().split()[2] + '\n')

f.close()
f2.close()
