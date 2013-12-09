#!/usr/bin/python

# depends on: bitarray, pulp, and glpk
# you can get them with something like:
# $ sudo easy_install bitarray
# $ sudo easy_install pulp
# $ brew install glpk
# that last one is if you're on a mac system with homebrew installed

import itertools, sys, copy, operator, string, datetime, random, time
from bitarray import bitarray
from pulp import *
from threading import Thread
from collections import defaultdict
import pickle

E = []
Ei = []
RE = []
REi = []
G = []
BL = []
NUM_NODES = 0
#MAX_PATH_LENGTH_FACTOR = .1

deepest = 0

FRAC = 0.01

exname = sys.argv[1].split('/')[-1]
path_result = 'paths/' + 'path_result_' + exname

try :
	st = time.time()
	with open(path_result, 'rb') as handle:
		FindPathResults = pickle.loads(handle.read())
	print 'reading dict', time.time() - st
except IOError:
	FindPathResults = {} # dictionary for dynmaic programming

#f_lp = open('lptime_result', 'w')
#f2 = open('avg_bitrate_result_temp', 'w')
#f1 = open('rounded_avg', 'w')
#f2 = open('no_rounded_avg', 'w')

# Find ALL paths from _source_ (int) to _dest_ (int) given a bit vector _eb_ that
# determines which edges in E to consider
def FindPath(eb, source, dest, result, depth):
	# limit the serching levels
    #if depth > 3:
    #    return
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
    #print '**inside h', h, 'P', P_All
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
    for i,e in enumerate(E): # (source, dest, bitrate)
        c = e[2]
        fs = []
        for j,g in enumerate(ST):
            for k, s in enumerate(g):
                if s[i]:
                    fs += [f[j][k]]
        prob += lpSum(fs) <= c
    #print prob

    for g,v in enumerate(G): # groups
        for t,v2 in enumerate(v[2]): # terminals
            prob += d[g][t] <= lpSum(f[g])   # bitrate level must be less than all ST for group
     #       print prob
            prob += d[g][t] <= BL[g][-1]     # don't exceed maximum bitrate level for group
     #       print prob
            # do we need this last constraint?

    w = [g[0] for g in G] # group weights
    n = [len(g[2]) for g in G] # number of terminals
    wn = [x*y for x,y in zip(w,n)]

    # v[g][t] - terminal weights
    v = []
    for g in G:
        v += [[t[1] for t in g[2]]]

    # w_0*n_0*[v_0,1 * d_0_1] + ....
    prob += lpDot(wn, [lpDot(v[g], d[g]) for g,k in enumerate(G)])
    #print prob

    status = prob.solve(GLPK(msg = 0))
    #print prob

    return (d, f)

roundedbl = []
#mintreecapa = []
def LPStep2(ST, d, f):
	d2 = []
	for g,v in enumerate(G):
		d2 += [[LpVariable("d2" + '-' + str(v[2].index(t)) + "-" + str(g), 0) for t in v[2]]]
#
	f2 = []
	for i,v in enumerate(ST):
		f2 += [[LpVariable("f2" + '-' + str(i) + "-" + str(v.index(t)), 0) for t in v]]

	# set initial values to rounded bitrates
    #"""
    #for g,v in enumerate(G):
    	#for x in 
        #no_total_d.append(sum([value(x) for x in d[g]]))
        ##value_d.append([value(x) for x in d[g]])
        #print 'd', [value(x) for x in d[g]]
        #print 'f', [value(x) for x in f[g]]
        #"""

	prob = LpProblem("myProblem2", LpMaximize)
	ssum = 0
	for i,e in enumerate(E):
		c = e[2]
		fs2 = []
		fs = []
		for j,g in enumerate(ST):
			for st,s in enumerate(g):
				if s[i]:
					fs2 += [f2[j][st]]
					fs += [value(f[j][st])]
		#print '***sum***', sum(fs), c
		ssum += (c - sum(fs))
		prob += lpSum(fs2) + sum(fs) <= c
	print ssum, ssum/len(E) 

	for g,v in enumerate(G):
		for t,v2 in enumerate(v[2]):
			prob += d2[g][t] <= lpSum(f2[g])   # bitrate level must be less than all ST for group
			if roundedbl[g] == BL[g][-1] :
				prob += d2[g][t] <= 0 # already all the bitrates are occupied -> constraint needed?
			else :
				prob += d2[g][t] <= BL[g][-1] - BL[g][roundedbl[g]]     # don't exceed maximum bitrate level for group

	w = [g[0] for g in G]
	v = []
	for g in G:
		v += [[t[1] for t in g[2]]]

	prob += lpDot(w, [lpDot(v[g], d2[g]) for g,k in enumerate(G)])
	print prob
	status = prob.solve(GLPK(msg = 0))

	return (d2, f2)
			

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


def SoftStaticStrawman():
    # "Soft Static Approach" --> All groups pick best tree according to current traffic
    global G
    effective_weights = copy.deepcopy(E)
    total_soft_static = 0
    eb = len(E) * bitarray('1')

    avg_br = 0

    print 'Starting Soft Static Approach'
    #print 'Groups (' + str(len(G)) + '): ' + str(G)
    #print 'Bitrate Levels: ' + str(BL)
    #while True:

    ST = getST(eb)

    # Find best ST per group
    soft_static_edges = copy.deepcopy(effective_weights)
    best_ST = []
    for g in ST: # each group
        max_tree = (0,0)
        for i,s in enumerate(g): # each ST in group
            bottleneck = (0,0,float('inf'))
            for j,l in enumerate(s): # each edge in ST
                if l: # if edge in ST
                    bottleneck = min(bottleneck, soft_static_edges[j], key=lambda x:x[2])
            if bottleneck[2] > max_tree[1]:
                max_tree = (i, bottleneck)
        best_ST += [max_tree]

        # decrement link weights based on bottleneck
        if best_ST[-1][1]:
            for j,l in enumerate(g[best_ST[-1][0]]):
                if l: 
                    tup = soft_static_edges[j] 
                    dec = best_ST[-1][1][2]
                    soft_static_edges[j] = (tup[0],tup[1],tup[2]-dec)

    #print best_ST
    null_bv = len(E) * bitarray('0')
    for i,s in enumerate(best_ST):
        if best_ST[i][1]:
            best_ST[i] = ST[i][best_ST[i][0]]
        else:
            best_ST[i] = null_bv

    # Calculate bitrate for using best tree
    edge_count = defaultdict(int)
    for s in best_ST:
        for i,e in enumerate(s):
            if e:
                edge_count[i] += 1

    for i,e in enumerate(E):
        if edge_count[i]:
            effective_weights[i] = (e[0],e[1],e[2] / edge_count[i])

    soft_static_br = []
    for g,s in enumerate(best_ST): # each group's best ST
        bottleneck = float('inf')
        for i,e in enumerate(s): # each edge in ST
            if e: # if edge in ST
                bottleneck = min(bottleneck, effective_weights[i][2])
        if bottleneck == float('inf'):
            bottleneck = 0
        bottleneck = min(bottleneck, G[g][1][-1])
        for i,e in enumerate(s):
            if e:
                effective_weights[i] = (E[i][0],E[i][1],E[i][2] - bottleneck)
        soft_static_br += [len(G[g][2])*bottleneck]
        avg_br += bottleneck/len(G)
        G[g][1] = [b - bottleneck for b in G[g][1]]

    G = [g for g in G if g[1][-1] > 0]


    #print soft_static_br
    #print 'Total data pushed to edge this round: ' + str(sum(soft_static_br))
    total_soft_static += sum(soft_static_br)
#     if not sum(soft_static_br):
#         break
    print 'Average data rate of stream: %d' % avg_br
    f2.write('Average data rate of stream: ' + str(avg_br) + '\n')
    print 'Total data pushed to edge for soft static algo: ' + str(total_soft_static)

def getST(eb):
    ST = []
    starttime = time.time()
    for i,g in enumerate(G):
        P = []
        #print 'Working on next group (%s)' % i
        for t in g[2]:
            p = []
            FindPath(eb,0,t[0],p,0) # find all paths from n_0 to n_t
            P += [p]
            #print 'how many paths to terminal ' + str(t[0]) + ":" + str(len(p))
        ST += [MakeAllSteinerTrees(P)]
        #print 'how many ST\'s for current group: ' + str(len(ST[-1]))
        
    # save FindPathResults into file
    #with open(path_result, 'wb') as handle:
    #    pickle.dump(FindPathResults, handle)
    # save STs into file 

    # Group, ST, [nodes, edges]
    #for i,s in enumerate(ST):
    #    print 'how many ST\'s for group ' + str(i) + ':' + str(len(s))
    #    pass

    return ST

def MainAlgo():
    # Main algorithm
    total_br = []
    eb = len(E) * bitarray('1')
    
    print 'Starting Algorithm'
    #print 'Groups (' + str(len(G)) + '): ' + str(G)
    #print 'Bitrate Levels: ' + str(BL)
    print datetime.datetime.now()

    ST = getST(eb)

    starttime = time.time()
    (d,f) = LPStep(ST)
    lpt = time.time() - starttime

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
    #print req

    # may be same as sum(total_d) ?
    #s = 0
    #for i,group in enumerate(f):
    #    for x in group:
    #        s += len(G[i][2])*value(x)
    #total_br += [s]
    #print 'total_br', total_br

    total_d = []
    avg_d = []
    rounded_d = []
    no_total_d = []
    no_avg_d = []
    #value_d = []

	# d rounding
    for g,v in enumerate(G):
    	idx = 0
    	while idx < len(BL[g]) and BL[g][idx] <= value(d[g][0]):
    		idx += 1

    	if idx != 0:
    		rounded_d += [[BL[g][idx-1]] * len(d[g])]
    		roundedbl.append(idx-1)
    	else:
	    	rounded_d += [[0] * len(d[g])]
    		roundedbl.append(0)
    print rounded_d
    
    #(d2, f2) = LPStep2(ST, d, f)
    
    print 'roundedbl', roundedbl
    for g,v in enumerate(G):
		#no rounding
        no_total_d.append(sum([value(x) for x in d[g]]))
        #value_d.append([value(x) for x in d[g]])
        #print 'd', [value(x) for x in d[g]]
        #print 'f', [value(x) for x in f[g]]
        #print 'd2', [value(x) for x in d2[g]]
        #print 'f2', [value(x) for x in f2[g]]
        #total_d.append(sum([value(x) for x in d[g]]))
        total_d.append(sum(rounded_d[g]))
        avg_d.append(total_d[-1]/len(G[g][2]))
        no_avg_d.append(no_total_d[-1]/len(G[g][2]))
     
    #print 'norounded_d', norounded_d
    #print 'value_d', value_d
    #print 'original_d', d
    #print 'rounded_d', rounded_d
    #print 'total_d', total_d
    #print 'avg_d', avg_d
    avg_d = sum(avg_d)/len(avg_d) if len(avg_d) > 0 else 0
    no_avg_d = sum(no_avg_d)/len(no_avg_d) if len(no_avg_d) > 0 else 0
    #f_lp.write(str(lpt)+'\n')
    #f2.write(str(avg_d)+'\n')
    print 'Average data rate of stream: ' + str(avg_d)
    #f1.write('Average data rate of stream: ' + str(avg_d) + '\n')
    #print 'Average data rate of stream: ' + str(no_avg_d)
    #f2.write('Average data rate of stream: ' + str(no_avg_d) + '\n')

    #print 'Total data pushed to edge overall: ' + str(sum(total_d))
    return (req, ST, f, E, avg_d, lpt)


def DecisionEngine(g, sorted_E, strawman):
    global G, E, Ei, RE, REi, BL, NUM_NODES
    G = copy.deepcopy(g)
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

    NUM_NODES = len(REi)-1
    print 'Number of nodes: ' + str(NUM_NODES)

    if(strawman):
        return SoftStaticStrawman()
    else:
        return MainAlgo()

def main():
    global STCP_IN, STCP_LEN, STCP_SET, FindPathResults
    (g, sE) = file_parse(sys.argv[1])
    # stream testing
    #for i in xrange(len(g)):
    #for i in xrange(0,len(g),len(g)/100):
    #    DecisionEngine(g[0:i+1], sE, int(float(sys.argv[2])))

    # link testing

    starttime = time.time()
    #flat_edge = sum(sE.values(), [])
    #for i in xrange(1,101):
    ##for i in range(1, 101, 20):
         #sampledSE = random.sample(flat_edge, int((i/100.0)*len(flat_edge)))
##
         #SSE = defaultdict(list)
         #for (src, dest, bw) in sampledSE:
             #SSE[src] += [(src,dest,bw)]
         #SSE[0] = sE[0]
#
         #FindPathResults = {}
         #STCP_IN = []
         #STCP_LEN = 0
         #STCP_SET = set()
#
         #r = DecisionEngine(g, SSE, int(float(sys.argv[2])))
         #print 'LPtime :', r[5]

    r = DecisionEngine(g, sE, int(float(sys.argv[2])))
    print 'LPtime :', r[5]
    finishtime = time.time() - starttime
    print 'TOTALtime :', finishtime
#    f3.close()

#     # variance testing
#     random.seed()
#     for i in xrange(0,10,1):
#         g2 = []
#         for j in xrange(len(g)):
#             if random.random() >= i*FRAC:
#                 g2.append(g[j])
#         SSE = copy.deepcopy(sE)
#         for v in SSE.items():
#             for j,v2 in enumerate(v[1]):
#                 if random.random() < i*FRAC:
#                     k = random.gauss(1, .02)
#                     v[1][j] = (v2[0], v2[1], int(v2[2]*k))
#             pass
#         FindPathResults = {}
#         STCP_IN = []
#         STCP_LEN = 0
#         STCP_SET = set()

#         r = DecisionEngine(g2, SSE, int(float(sys.argv[2])))
#         print r

    # scalability testing
    #starttime = time.time()
    #r = DecisionEngine(g, sE, int(float(sys.argv[2])))
    #finishtime = time.time() - starttime
    #print 'LPtime :', r[5]
    #print 'TOTALtime :', finishtime
    #f2.close()
    #f1.close()
    #f_lp.close()


	#print r[5]
#     for num_workers in xrange(1, 11):
# #         FindPathResults = {}
# #         STCP_IN = []
# #         STCP_LEN = 0
# #         STCP_SET = set()
#         rt = 0
#         avg = 0
#         SSE = {}
#         for node, list in sE.items():
#             SSE[node] = [(l[0],l[1],l[2]/num_workers) for l in list]
#         for i in xrange(num_workers):
#             frac = int(len(g)/num_workers)
#             g2 = g[i*frac:(i+1)*frac]
#             avg_d = 0
#             r, st, f, e, avg_d, lpt = DecisionEngine(g2, SSE, int(float(sys.argv[2])))
#             rt = max(rt, lpt)
#             avg += avg_d*(1.0/num_workers)
#         print "RT for %d workers: %f" % (num_workers, rt)
#         print "RT avg for %d workers: %f" % (num_workers, avg)

if __name__ == '__main__':
    main()

