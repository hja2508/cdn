#!/usr/bin/python

# depends on: bitarray, pulp, and glpk
# you can get them with something like:
# $ sudo easy_install bitarray
# $ sudo easy_install pulp
# $ brew install glpk
# that last one is if you're on a mac system with homebrew installed

import itertools, sys, copy, operator
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
MAX_PATH_LENGTH_FACTOR = .1

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
                    if depth < len(REi) * MAX_PATH_LENGTH_FACTOR:
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
        r = len(REi) * bitarray('0')
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
    n = [len(g[2]) for g in G] # number of terminals
    wn = [x*y for x,y in zip(w,n)]

    prob += lpDot(wn, d)   # w_0*n_0*d_0 + w_1*n_1*d_1......

    status = prob.solve(GLPK(msg = 0))

    return (d, f)

def nodesin(A):
    for a in A:
        if a[2]:
            return True
    return False


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
#                 if weight < 5: # remove edges that are erroneous
#                     continue
                try:
                    sorted_E[src] += [(src,dest,weight)]
                except:
                    sorted_E += [[(src,dest,weight)]]

                unsorted_RE += [(src,dest,weight)]
            if group_on:
                br = l[2].translate(None, '{}[]kbps').strip().split(',')
                br = [eval(b) for b in br]
                T = l[3].translate(None, '{}[]').strip().split(',')
                T = [(node_map[eval(t.split('=')[0].split('_')[1])], eval(t.split('=')[1])) for t in T]
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

    total_br = []

    print 'Number of nodes: ' + str(len(REi))


#     # "Hard Static Approach" --> All groups pick maximum tree
#     print 'Starting Hard Static Approach'
#     print 'Groups (' + str(len(G)) + '): ' + str(G)
#     print 'Bitrate Levels: ' + str(BL)

#     ST = []
#     for i,g in enumerate(G):
#         P = []
#         print 'Working on next group (%s)' % i
#         for t in g[2]:
#             p = []
#             FindPath(eb,0,t[0],p,0) # find all paths from n_0 to n_t
#             P += [p]
#             #print 'how many paths to terminal ' + str(t[0]) + ":" + str(len(p))
#         ST += [MakeAllSteinerTrees(P)]
#         #print 'how many ST\'s for current group: ' + str(len(ST[-1]))


#     # Group, ST, [nodes, edges]
#     for i,s in enumerate(ST):
#         print 'how many ST\'s for group ' + str(i) + ':' + str(len(s))

#     # Find best ST per group
#     best_ST = []
#     for g in ST: # each group
#         max_tree = (0,0)
#         for i,s in enumerate(g): # each ST in group
#             bottleneck = (0,0,float('inf'))
#             for j,l in enumerate(s): # each edge in ST
#                 if l: # if edge in ST
#                     bottleneck = min(bottleneck, E[j], key=lambda x:x[2])
#             if bottleneck[2] > max_tree[1]:
#                 max_tree = (i, bottleneck)
#         best_ST += [max_tree]
    
#     print best_ST
#     for i,s in enumerate(best_ST):
#         best_ST[i] = ST[i][best_ST[i][0]]
    
#     # Calculate bitrate for using best tree
#     edge_count = defaultdict(int)
#     for s in best_ST:
#         for i,e in enumerate(s):
#             if e:
#                 edge_count[i] += 1
                
#     effective_weights = {}
#     for i,e in enumerate(E):
#         if edge_count[i]:
#             effective_weights[i] = e[2] / edge_count[i]

#     hard_static_br = []
#     for s in best_ST: # each group's best ST
#         bottleneck = float('inf')
#         for i,e in enumerate(s): # each edge in ST
#             if e: # if edge in ST
#                 bottleneck = min(bottleneck, effective_weights[i])
#         hard_static_br += [bottleneck]

#     print hard_static_br
#     print 'Total data pushed through trees overall: ' + str(sum(hard_static_br))


#     effective_weights = copy.deepcopy(E)
#     total_soft_static = 0

#     # "Soft Static Approach" --> All groups pick best tree according to current traffic
#     print 'Starting Soft Static Approach'
#     while True:
#         print 'Groups (' + str(len(G)) + '): ' + str(G)
#         print 'Bitrate Levels: ' + str(BL)

#         ST = []
#         for i,g in enumerate(G):
#             P = []
#             print 'Working on next group (%s)' % i
#             for t in g[2]:
#                 p = []
#                 FindPath(eb,0,t[0],p,0) # find all paths from n_0 to n_t
#                 P += [p]
#                 #print 'how many paths to terminal ' + str(t[0]) + ":" + str(len(p))
#             ST += [MakeAllSteinerTrees(P)]
#             #print 'how many ST\'s for current group: ' + str(len(ST[-1]))


#         # Group, ST, [nodes, edges]
#         for i,s in enumerate(ST):
#             print 'how many ST\'s for group ' + str(i) + ':' + str(len(s))



#         # Find best ST per group
#         soft_static_edges = copy.deepcopy(effective_weights)
#         best_ST = []
#         for g in ST: # each group
#             max_tree = (0,0)
#             for i,s in enumerate(g): # each ST in group
#                 bottleneck = (0,0,float('inf'))
#                 for j,l in enumerate(s): # each edge in ST
#                     if l: # if edge in ST
#                         bottleneck = min(bottleneck, soft_static_edges[j], key=lambda x:x[2])
#                 if bottleneck[2] > max_tree[1]:
#                     max_tree = (i, bottleneck)
#             best_ST += [max_tree]

#             # decrement link weights based on bottleneck
#             if best_ST[-1][1]:
#                 for j,l in enumerate(g[best_ST[-1][0]]):
#                     if l: 
#                         tup = soft_static_edges[j] 
#                         dec = best_ST[-1][1][2]
#                         soft_static_edges[j] = (tup[0],tup[1],tup[2]-dec)
    
#         print best_ST
#         null_bv = len(E) * bitarray('0')
#         for i,s in enumerate(best_ST):
#             if best_ST[i][1]:
#                 best_ST[i] = ST[i][best_ST[i][0]]
#             else:
#                 best_ST[i] = null_bv
    
#         # Calculate bitrate for using best tree
#         edge_count = defaultdict(int)
#         for s in best_ST:
#             for i,e in enumerate(s):
#                 if e:
#                     edge_count[i] += 1
                
#         for i,e in enumerate(E):
#             if edge_count[i]:
#                 effective_weights[i] = (e[0],e[1],e[2] / edge_count[i])

#         soft_static_br = []
#         for g,s in enumerate(best_ST): # each group's best ST
#             bottleneck = float('inf')
#             for i,e in enumerate(s): # each edge in ST
#                 if e: # if edge in ST
#                     bottleneck = min(bottleneck, effective_weights[i][2])
#             if bottleneck == float('inf'):
#                 bottleneck = 0
#             for i,e in enumerate(s):
#                 if e:
#                     effective_weights[i] = (E[i][0],E[i][1],E[i][2] - bottleneck)
#             soft_static_br += [len(G[g][2])*bottleneck]

#         print soft_static_br
#         print 'Total data pushed to edge this round: ' + str(sum(soft_static_br))
#         total_soft_static += sum(soft_static_br)
#         if not sum(soft_static_br):
#             break
#     print 'Total data pushed to edge for soft static algo: ' + str(total_soft_static)

    # Main algorithm
    
    G_br = []

    while nodesin(G):
        print 'Starting New Algorithm Round'
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

        # lower the BW on all links according to the LP step
        for g,v in enumerate(ST): #groups
            for t,v2 in enumerate(v): # diff ST's
                for i,j in enumerate(v2):
                    if j:
                        E[i] = (E[i][0], E[i][1], E[i][2] - value(f[g][t]))

        s = 0
        for i,group in enumerate(f):
            g_b = 0
            for x in group:
                s += len(G[i][2])*value(x)
                g_b += value(x)
            if len(G_br) > i:
                G_br[i] += g_b
            else:
                G_br += [g_b]
        total_br += [s]
        #total_d += [sum([value(x) for x in d])]
        print 'Total data pushed to edge this round: ' + str(total_br[-1]) + '\n'

        # lower the max BRL
        for i,g in enumerate(G):
            BL[i] = [max(0,b-value(d[i])) for b in BL[i]]
            if not BL[i][-1]:
                # If we've already gotten max BW remove the group
                #del BL[i]
                #del G[i]
                pass

        # remove the terminal with the least weight
        for g in G:
            if g[2]:
                t = min(g[2], key=lambda x:x[1])
                g[2].remove(t)
        #G = [g for g in G if g[2]]
        

    print 'Total data pushed to edge overall: ' + str(sum(total_br))
    print G_br
    print G


DecisionEngine(sys.argv[1])
