#!/usr/bin/python

# depends on: cython, bitarray, pulp, and glpk
# you can get them with something like:
# $ sudo easy_install cython
# $ sudo easy_install bitarray
# $ sudo easy_install pulp
# $ brew install glpk
# that last one is if you're on a mac system with homebrew installed

import itertools, sys, copy, operator
from bitarray import bitarray
from pulp import *

E = []
Ei = []
RE = []
REi = []
G = []
BL = []

def removeE(eb, n):
    # remove all edges starting at n from BV
    e = bitarray(eb)
    e[Ei[n]:Ei[n+1]] = (Ei[n+1]-Ei[n]) * bitarray([False])

    # remove all edges ending at n from BV
    B = RE[REi[n]:REi[n+1]] # edges to remove
    for b in B:
        e[b] = False
    return e

FindPathResults = {} # dictionary for dynmaic programming

# Find ALL paths from _source_ (int) to _dest_ (int) given a bit vector _eb_ that
# determines which edges in E to consider
def FindPath(eb, source, dest):
    h = str(source)+str(dest)+eb.to01() # index for dynamic programming array

    # dynamic programming
    try:
        P = FindPathResults[h] 
        return P
    except KeyError:
        pass

    # list of all paths from _source_ to _dest_ using edges from BV _eb_
    P_All = []
    try:
        for i in range(Ei[source], Ei[source+1]): # indices of all edges starting at source
            if eb[i]: # if this edge is being currently used in the BV
                e = removeE(eb, source) # create a new BV without edges to/from source
                c = E[i][1] # child of current source node we want to consider

                if c == dest: # we're done!
                    # construct a BV using only the edge from current source to current child
                    bv = len(eb) * bitarray('0')
                    bv[i] = True
                    P = [bv] # the only path using the edge (source, dest) to dest is this one
                else:
                    P = FindPath(e, c, dest) # see if current child can reach dest in some way
                    P = [p for p in P if p] # remove null paths
                    for p in P:
                        p[i] = True # Include the edge from current source to current child
                P_All += P # Store this set of paths so we can consider a new child
    except IndexError: # this node has no children --> P_All will be [] (i.e. no paths to dest)
        pass
    FindPathResults[h] = P_All # store results for dynamic programming
    return P_All

# Given all the paths to nodes in a given group, compute all the steiner trees (ST's)
def MakeAllSteinerTrees(P):
    ST = []
    p = itertools.product(*P) # make all combinations of paths to all nodes

    # each 'paths' is a list of individual paths to the set of nodes in the group
    # as each path is just a BV of edges, we can bitwise-or them together to get the overall graph
    p = [reduce(operator.or_, paths) for paths in p]

    # remove duplicate BV's
    d = {s.to01():s for s in p}
    p = list(d.values())

    # we now need to check if this graph is actually a tree
    # we just look to see if we see the same node as a destination to more than one edge
    for bv in p:
        r = len(REi) * bitarray('0')
        for i,e in enumerate(E): # this could be better -- O(|E|)
            if bv[i]: # if we're even using this edge in our ST
                if r[e[1]]: # if we've already seen this destination ndoe
                    bv = None # not a tree!
                    break
                else: # never seen this destination node
                    r[e[1]] = True
        if bv: # This graph is a tree
            ST += [bv] # add it to our collection of ST's
    return ST

# Calc the bit rate level (i.e. the sum of all the bitrates less than this bit rate)
def CalcBitrateLevel(g):
    for i in range(1, len(g[1])):
        g[1][i] = g[1][i]+g[1][i-1]
    return g[1]

# Given a list of lists (i.e. all the steiner trees for all the groups) of ST's 
# calc the global optimal based on our LP problem
def LPStep(ST):
    # d[g] for g \in G
    d = [LpVariable("d" + str(G.index(g)), 0) for g in G]

    # f[g][st] for g \in G, st \in ST \in G
    f = []
    for i,v in enumerate(ST):
        f += [[LpVariable("f" + str(i) + "-" + str(v.index(t)), 0) for t in v]]

    prob = LpProblem("myProblem", LpMaximize)

    # have all ST's that use a given link be less than the total link BW
    for e in E: # (source, dest, bitrate)
        c = e[2]
        fs = []
        for g in ST:
            for s in g:
                if s[E.index(e)]:
                    fs += [f[ST.index(g)][g.index(s)]]
        prob += lpSum(fs) <= c

    for g,v in enumerate(ST): # groups
        prob += d[g] <= lpSum(f[g])   # bitrate level must be less than all ST for group
        prob += d[g] <= BL[g][-1]     # don't exceed maximum bitrate level for group
        # do we need this last constraint?

    w = [g[0] for g in G] # group weights

    prob += lpDot(w, d)   # w_0*d_0 + w_1*d_1......

    status = prob.solve(GLPK(msg = 0))

    return (d, f)


def DecisionEngine(file_name):
    global G, E, Ei, RE, REi, BL
    sorted_E = []
    unsorted_RE = []

    f = open(file_name, 'r').read().split('\n')

    link_on = False
    group_on = False

    max_node = 0
    node_map = {}

    # File parsing code
    for l in f:
        l = l.strip()
        if len(l) == 0 or (l[0] == '/' and l[1] == '/'):
            continue
        else:
            if l == 'Link:':
                link_on = True
                group_on = False
                continue
            if l == 'Groups:':
                link_on = False
                group_on = True
                continue

            l = l.split('\t')
            if link_on:
                try:
                    src = node_map[eval(l[2].split('_')[1])]
                except:
                    node_map[eval(l[2].split('_')[1])] = max_node
                    src = max_node
                    max_node += 1
                try:
                    dest = node_map[eval(l[3].split('_')[1])]
                except:
                    node_map[eval(l[3].split('_')[1])] = max_node
                    dest = max_node
                    max_node += 1
                weight = eval(l[1].translate(None,'[]{}kbps'))
                if weight < 5: # remove edges that are erroneous
                    continue
                try:
                    sorted_E[src] += [(src,dest,weight)]
                except:
                    sorted_E += [[(src,dest,weight)]]

                unsorted_RE += [(src,dest,weight)]
            if group_on:
                br = l[2].translate(None, '{}[]kbps').strip().split(',')
                br = [eval(b) for b in br]
                T = l[3].translate(None, '{}[]').strip().split(',')
                T = [(eval(t.split('=')[0].split('_')[1]), eval(t.split('=')[1])) for t in T]
                G += [[eval(l[1]), br, T]]
        
    # Build up flat edge list (E) and edge index (Ei)
    E = [item for sublist in sorted_E for item in sublist]
    Ei = [len(sorted_E[0])]
    for i in range(1,len(sorted_E)):
        Ei += [Ei[i-1]+len(sorted_E[i])]
    Ei = [0] + Ei
    eb = len(E) * bitarray('1')

    # Build up the reverse edge list (RE) and it's index (REi)
    RE = [e for e in unsorted_RE ]
    RE = sorted(RE, key=lambda x:x[1])
    n = 0
    for i,e in enumerate(RE):
        if e[1] == n:
            continue
        else:
            while n != e[1]:
                REi += [i]
                n += 1
    REi = [0] + REi
    for i,e in enumerate(RE):
        RE[i] = E.index(e)

    for g in G:
        BL += [CalcBitrateLevel(g)]

    total_d = []

    # Main algorithm
    while G:
        print 'Groups: ' + str(G)
        print 'Bitrate Levels: ' + str(BL)

        ST = []
        for g in G:
            P = []
            print 'Working on next group'
            for t in g[2]:
                p = FindPath(eb,0,t[0]) # find all paths from n_0 to n_t
                P += [p]
                print 'how many paths to terminal ' + str(t[0]) + ":" + str(len(p))
            ST += [MakeAllSteinerTrees(P)]

        # Group, ST, [nodes, edges]
        for i,s in enumerate(ST):
            print 'how many ST\'s for group ' + str(i) + ':' + str(len(s))

        (d,f) = LPStep(ST)

        # lower the BW on all links according to the LP step
        for g,v in enumerate(ST): #groups
            for t,v2 in enumerate(v): # diff ST's
                for i,j in enumerate(v2):
                    if j:
                        E[i] = (E[i][0], E[i][1], E[i][2] - value(f[g][t]))

        # lower the max BRL
        for i,g in enumerate(G):
            BL[i] = [max(0,b-value(d[i])) for b in BL[i]]

        # remove the terminal with the least weight
        for g in G:
            t = min(g[2], key=lambda x:x[1])
            g[2].remove(t)
        G = [g for g in G if g[2]]

        total_d += [sum([value(x) for x in d])]
        print 'Total data pushed through trees this round: ' + str(total_d[-1])

    print 'Total data pushed through trees overall: ' + str(sum(total_d))
