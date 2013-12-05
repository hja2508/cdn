#! /usr/bin/python

from bitarray import bitarray
import pickle

a = {
	'a': bitarray('001'),
	'b': bitarray('010')
}

with open('result.txt', 'wb') as handle:
	pickle.dump(a, handle)

with open('result.txt', 'rb') as handle:
	b = pickle.loads(handle.read())

print b['b'].tobytes()
print a['b'].tobytes()
#print b

