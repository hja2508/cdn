#!/usr/bin/python

# depends on: bitarray, pulp, and glpk
# you can get them with something like:
# $ sudo easy_install bitarray
# $ sudo easy_install pulp
# $ brew install glpk
# that last one is if you're on a mac system with homebrew installed

import itertools, sys, copy, operator, string
from bitarray import bitarray
from pulp import *
from threading import Thread
from collections import defaultdict

E = []
Ei = []
RE = []
REi = []
G = []
BL = []
NUM_NODES = 0
#MAX_PATH_LENGTH_FACTOR = .1

deepest = 0

FindPathResults = {} # dictionary for dynmaic programming

# Find ALL paths from _source_ (int) to _dest_ (int) given a bit vector _eb_ that
# determines which edges in E to consider
def FindPath(eb, source, dest, result, depth):
    global deepest
    if depth > deepest:
        deepest = depth

    h = str(source)+str(dest)+eb.to01() # index for dynamic programming array

    # dynamic programming
    try:
        P = FindPathResults[h] 
        result += P
        return
    except KeyError:
        pass

    # list of all paths from _source_ to _dest_ using edges from BV _eb_
    P_All = []
    try:
        t = []
        # set up a list for each child to store their results in
        for i in range(Ei[source], Ei[source+1]):
            P_All += [[]]
        for i in range(Ei[source], Ei[source+1]): # indices of all edges starting at source
            if eb[i]: # if this edge is being currently used in the BV
                # create a new BV without edges to/from source
                # remove all edges starting at n from BV
                e = bitarray(eb)
                e[Ei[source]:Ei[source+1]] = (Ei[source+1]-Ei[source]) * bitarray([False])
                # remove all edges ending at n from BV
                B = RE[REi[source]:REi[source+1]] # edges to remove
                for b in B:
                    e[b] = False

                c = E[i][1] # child of current source node we want to consider
                if c == dest: # we're done!
                    # construct a BV using only the edge from current source to current child
                    bv = len(eb) * bitarray('0')
                    bv[i] = True
                    P_All[i-Ei[source]] = [bv] # the only path using the edge (source, dest) to dest is this one
                else:
                    # see if current child can reach dest in some way
                    #if depth < NUM_NODES * MAX_PATH_LENGTH_FACTOR:
                    FindPath(e, c, dest, P_All[i-Ei[source]], depth+1)

        for i,P in enumerate(P_All):
            P = [p for p in P if p] # remove null paths
            for p in P:
                p[i+Ei[source]] = True # Include the edge from current source to current child
                
    except IndexError: # this node has no children --> P_All will be [] (i.e. no paths to dest)
        pass

    P_All = [p for p in P_All if p] # remove null paths
    P_All = [item for sublist in P_All for item in sublist] # flatten list down for children

    FindPathResults[h] = P_All # store results for dynamic programming
    result += P_All

STCP_IN = []
STCP_LEN = 0
STCP_SET = set()

# Find all ways to combine paths to individual nodes to form all possible steiner trees
def STCP(i, accum): # Set of all Sets of paths    
    # each 'paths' is a list of individual paths to the set of nodes in the group
    # as each path is just a BV of edges, we can bitwise-or them together to get the overall graph
    if i < STCP_LEN:
        # we now need to check if this graph is actually a tree
        # we just look to see if we see the same node as a destination to more than one edge
        r = NUM_NODES * bitarray('0')
        for j,e in enumerate(E): # this could be better -- O(|E|)
            if accum[j]: # if we're even using this edge in our ST
                if r[e[1]]: # if we've already seen this destination ndoe
                    return # not a tree!
                else: # never seen this destination node
                    r[e[1]] = True
        # This graph is a tree
        # for one selection of P[0]
        # all the BV's using that selection
        [STCP(i+1, accum | s) for s in STCP_IN[i]]
    else:
        # remove duplicate BV's
        STCP_SET.add(accum.to01())

# Given all the paths to nodes in a given group, compute all the steiner trees (ST's)
def MakeAllSteinerTrees(P):
    global STCP_IN, STCP_LEN, STCP_SET
    ST = []    

    # Create all possible Steiner Trees
    a = len(E) * bitarray('0')
    STCP_IN = P
    STCP_LEN = len(P)
    STCP_SET = set()
    STCP(0, a)
    ST = [bitarray(x) for x in STCP_SET]

    return ST

# Calc the bit rate level (i.e. the sum of all the bitrates less than this bit rate)
def CalcBitrateLevel(g):
    for i in range(1, len(g[1])):
        g[1][i] = g[1][i]+g[1][i-1]
    return g[1]

# Given a list of lists (i.e. all the steiner trees for all the groups) of ST's 
# calc the global optimal based on our LP problem
def LPStep(ST):
    # d[g][t] for t \in g \in G
    d = []
    for g,v in enumerate(G):
        d += [[LpVariable("d" + str(v[2].index(t)) + "-" + str(g), 0) for t in v[2]]]

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

    for g,v in enumerate(G): # groups
        for t,v2 in enumerate(v[2]): # terminals
            prob += d[g][t] <= lpSum(f[g])   # bitrate level must be less than all ST for group
            prob += d[g][t] <= BL[g][-1]     # don't exceed maximum bitrate level for group
            # do we need this last constraint?

    w = [g[0] for g in G] # group weights
    n = [len(g[2]) for g in G] # number of terminals
    wn = [x*y for x,y in zip(w,n)]

    # v[g][t]
    v = []
    for g in G:
        v += [[t[1] for t in g[2]]]

    # w_0*n_0*[v_0,1 * d_0_1] + ....
    prob += lpDot(wn, [lpDot(v[g], d[g]) for g,k in enumerate(G)])

    status = prob.solve(GLPK(msg = 0))

    return (d, f)

def nodesin(A):
    for a in A:
        if a[2]:
            return True
    return False


def file_parse(file_name):
    sorted_E = {}
    g = []

    f = open(file_name, 'r').read().split('\n')

    link_on = False
    group_on = False

    max_node = 0

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
                src = eval(l[2].split('_')[1])
                dest = eval(l[3].split('_')[1])
                weight = eval(l[1].translate(string.maketrans("","",),'[]{}kbps'))
#                 if weight < 5: # remove edges that are erroneous
#                     continue
                try:
                    sorted_E[src] += [(src,dest,weight)]
                except:
                    sorted_E[src] = [(src,dest,weight)]

            if group_on:
                br = l[2].translate(string.maketrans("","",), '{}[]kbps').strip().split(',')
                br = [eval(b) for b in br]
                T = l[3].translate(string.maketrans("","",), '{}[]').strip().split(',')
                T = [(eval(t.split('=')[0].split('_')[1]), eval(t.split('=')[1])) for t in T]
                g += [[eval(l[1]), br, T]]
    return (g, sorted_E)



def DecisionEngine(g, sorted_E):
    global G, E, Ei, RE, REi, BL, NUM_NODES
    G = g
    E = []
    Ei = []
    RE = []
    REi = []
    BL = []


    # Build up flat edge list (E) and edge index (Ei)
    Ei = [len(sorted_E[0])]
    for i in range(1,max(sorted_E)+1):
        try:
            Ei += [Ei[i-1]+len(sorted_E[i])]
        except:
            Ei += [Ei[i-1]]
    sorted_E = [sorted_E[k] for k in sorted(sorted_E)]
    E = [item for sublist in sorted_E for item in sublist]
    Ei = [0] + Ei
    eb = len(E) * bitarray('1')

    # Build up the reverse edge list (RE) and it's index (REi)
    RE = sorted(E, key=lambda x:x[1])
    n = 0
    for i,e in enumerate(RE):
        if e[1] == n:
            continue
        else:
            while n != e[1]:
                REi += [i]
                n += 1
    REi = [0] + REi + [len(RE)]
    for i,e in enumerate(RE):
        RE[i] = E.index(e)

    for g in G:
        BL += [CalcBitrateLevel(g)]

    total_br = []

    NUM_NODES = len(REi)-1
    print 'Number of nodes: ' + str(NUM_NODES)

    # Main algorithm
    
    print 'Starting Algorithm'
    print 'Groups (' + str(len(G)) + '): ' + str(G)
    print 'Bitrate Levels: ' + str(BL)

    ST = []
    for i,g in enumerate(G):
        P = []
        print 'Working on next group (%s)' % i
        for t in g[2]:
            p = []
            FindPath(eb,0,t[0],p,0) # find all paths from n_0 to n_t
            P += [p]
            #print 'how many paths to terminal ' + str(t[0]) + ":" + str(len(p))
        ST += [MakeAllSteinerTrees(P)]
        #print 'how many ST\'s for current group: ' + str(len(ST[-1]))


    # Group, ST, [nodes, edges]
    for i,s in enumerate(ST):
        print 'how many ST\'s for group ' + str(i) + ':' + str(len(s))

    (d,f) = LPStep(ST)

    req = {}
    for i in xrange(NUM_NODES):
        req[i] = {}
    for g,ss in enumerate(ST):
        for j,s in enumerate(ss):
            for k in xrange(len(E)):
                if s[k] and value(f[g][j]):
                    try:
                        req[E[k][1]][g] += [(E[k][0], value(f[g][j]))]
                    except:
                        req[E[k][1]][g] = [(E[k][0], value(f[g][j]))]
    print req

    s = 0
    for i,group in enumerate(f):
        for x in group:
            s += len(G[i][2])*value(x)
    total_br += [s]

    total_d = []
    for g,v in enumerate(G):
        total_d.append(sum([value(x) for x in d[g]]))
    print total_d

    print 'Total data pushed to edge overall: ' + str(sum(total_br))
    return req

if __name__ == '__main__':
    (g, sE) = file_parse(sys.argv[1])
    DecisionEngine(g, sE)
