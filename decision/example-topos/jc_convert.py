#!/usr/bin/python

d = eval(open('gen_example_link_capacity_map').read().split('\n')[0])

for k,v in d.items():
    for e in v:
        print e
