#!/usr/bin/python

import itertools, sys

def children(edges, source):
    try:
        return [x[0] for x in edges[source]]
    except KeyError:
        return []

def removeSE(edges, source):
    e = dict(edges)
    e[source] = []
    for v in e:
        for l in e[v]:
            if l[0] == source:
                e[v].remove(l)
    return e

FindPathResults = {}

def FindPath(vert, edges, source, dest):
    if source == dest:
        return [[dest]]

    h = hash(repr(sorted(vert)+sorted(edges.items())+[source]+[dest]))
    try:
        P = FindPathResults[h]
        return P
    except KeyError:
        pass

    P_All = []
    for c in children(edges, source):
        v = list(vert)
        v.remove(source)
        e = dict(edges)
        e = removeSE(e, source)
        P = FindPath(v, e, c, dest)
        P = [[source]+p for p in P if p[-1] == dest]
        P_All = P_All + P
    FindPathResults[h] = P_All
    return P_All

def CombinePaths(p):
    v = sorted(list(set([x for y in p for x in y])))
    e = {}
    r = {}
    cycle = False
    for path in p:
        for i in range(len(path)):
            if i+1 < len(path):
                try:
                    e[path[i]] = list(set(e[path[i]]+[path[i+1]]))
                except:
                    e[path[i]] = [path[i+1]]
            if i-1 >= 0:
                try:
                    r[path[i]] = list(set(r[path[i]]+[path[i-1]]))
                    if len(r[path[i]]) > 1:
                        cycle = True
                except:
                    r[path[i]] = [path[i-1]]
    if cycle == False:
        return (v,e)
    else:
        return ([],[])

def MakeAllSteinerTrees(P):
    ST = []
    p = list(itertools.product(*P))
    for paths in p:
        s = CombinePaths(paths)
        if s[0]:
            ST.append(s)
    return ST






f = open(sys.argv[1], 'r').read().split('\n')

node_on = False
link_on = False
group_on = False
V = []
E = {}
G = []


for l in f:
    l = l.strip()
    if len(l) == 0 or (l[0] == '/' and l[1] == '/'):
        continue
    else:
        if l == 'Node:':
            node_on = True
            link_on = False
            group_on = False
            continue
        if l == 'Link:':
            node_on = False
            link_on = True
            group_on = False
            continue
        if l == 'Groups:':
            node_on = False
            link_on = False
            group_on = True
            continue

        if node_on:
            V = V + [l]
        if link_on:
            try:
                E[l.split('\t')[2]].append((l.split('\t')[3], l.split('\t')[1]))
            except:
                E[l.split('\t')[2]] = [(l.split('\t')[3], l.split('\t')[1])]
        if group_on:
            G = G + [l.split('\t')]
        
# print V
# print E
# print G

for g in G:
    N = g[3].split(',')
    P = []
    for n in N:
        n = n.split('=')[0].replace("{","").strip()
        P.append(FindPath(V,E,'n_0',n))
    ST = MakeAllSteinerTrees(P)
    #print ST

