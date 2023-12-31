#!/usr/bin/env python
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gs
import matplotlib as mpl
from readPatchOutput import *
from plotV1_response import ellipse
np.seterr(invalid = 'warn')

import sys
output_suffix = sys.argv[1]
res_suffix = sys.argv[2]
conLGN_suffix = sys.argv[3]
conV1_suffix = sys.argv[4]
res_fdr = sys.argv[5]
setup_fdr = sys.argv[6]
data_fdr = sys.argv[7]
fig_fdr = sys.argv[8]
print(f'output figures to {fig_fdr}')

if res_suffix:
    res_suffix = "-" + res_suffix 
if conLGN_suffix:
    conLGN_suffix = "-" + conLGN_suffix 
if conV1_suffix:
    conV1_suffix = "-" + conV1_suffix 
if output_suffix:
    output_suffix = "-" + output_suffix

print(f'res_suffix = {res_suffix}')
print(f'conLGN_suffix = {conLGN_suffix}')
print(f'conV1_suffix = {conV1_suffix}')
print(f'output_suffix = {output_suffix}')

if fig_fdr[-1] != "/":
    fig_fdr = fig_fdr + "/"
if res_fdr[-1] != "/":
    res_fdr = res_fdr + "/"
if setup_fdr[-1] != "/":
    setup_fdr = setup_fdr + "/"
if data_fdr[-1] != "/":
    data_fdr = data_fdr + "/"

seed = 6578873
np.random.seed(seed)
ns = 12
mk = ['o', 'd']
compThres = 1
#sample = np.array([])

plotStats = True
#plotLGNsSize = True
#plotPos = True
#plotLGN_V1_sample = True
#plot_nLGN_OS = True
plotConFeature_stats = True 
plotConFeature_preSynTC = True
plotConFeature_sample = True
plotCon_sample = True
#plotLGN_V1_ratio = True
#plotLGNsSum = True
#plotBlockWiseComplexDist = True

#plotStats = False
plotLGNsSize = False
plotPos = False
plotLGN_V1_sample = False 
plot_nLGN_OS = False
#plotConFeature_stats = False
#plotConFeature_preSynTC = False
#plotConFeature_sample = False 
#plotCon_sample = False
plotLGN_V1_ratio = False
plotLGNsSum = False
plotBlockWiseComplexDist = False 

LGN_vposFn = res_fdr + 'LGN_vpos'+ res_suffix + ".bin"
featureFn = res_fdr + 'V1_feature' + res_suffix + ".bin"
V1_allposFn = res_fdr + 'V1_allpos' + res_suffix + ".bin"
parameterFn = data_fdr + "patchV1_cfg" + output_suffix + ".bin"

conMat_file = setup_fdr + 'V1_conMat' + conV1_suffix + '.bin'
delayMat_file = setup_fdr + 'V1_delayMat' + conV1_suffix + '.bin'
vec_file = setup_fdr + 'V1_vec' + conV1_suffix + '.bin'
blkPos_file = setup_fdr + 'block_pos' + conV1_suffix + '.bin'
nabaBlk_file = setup_fdr + 'neighborBlock' + conV1_suffix + '.bin'
stats_file = setup_fdr + 'conStats' + conV1_suffix + '.bin'
connectomeFn = setup_fdr + "connectome_cfg" + conV1_suffix + ".bin"

LGN_V1_ID_file = setup_fdr + 'LGN_V1_idList' + conLGN_suffix + '.bin'
LGN_V1_s_file = setup_fdr + 'LGN_V1_sList' + conLGN_suffix + '.bin'

prec, sizeofPrec, vL, vE, vI, vR, vThres, gL, vT, typeAcc, nE, nI, sRatioLGN, sRatioV1, frRatioLGN, convolRatio, nType, nTypeE, nTypeI, frameRate, inputFn, virtual_LGN, _, _ = read_cfg(parameterFn)

typeAcc = np.hstack((0, typeAcc))
print(typeAcc)

sampleBlockId = [13]

with open(V1_allposFn, 'rb') as f:
    nblock = np.fromfile(f, 'u4', count=1)[0]
    blockSize = np.fromfile(f, 'u4', count=1)[0]
    networkSize = nblock*blockSize
    dataDim = np.fromfile(f, 'u4', count=1)[0]
    assert(blockSize == typeAcc[-1])
    print([nblock,blockSize,networkSize,dataDim])
    coord_span = np.fromfile(f, 'f8', count=4)
    V1_x0 = coord_span[0]
    V1_xspan = coord_span[1]
    V1_y0 = coord_span[2]
    V1_yspan = coord_span[3]
    print(f'V1_x:{[V1_x0, V1_x0 + V1_xspan]}')
    print(f'V1_y:{[V1_y0, V1_y0 + V1_yspan]}')
    _pos = np.reshape(np.fromfile(f, 'f8', count = networkSize*2), (2,nblock,blockSize))
    pos = np.empty((nblock,2,blockSize), dtype = 'f8')
    for i in range(nblock):
        pos[i,0,:] = _pos[0,i,:]
        pos[i,1,:] = _pos[1,i,:]

# read block center pos
with open(blkPos_file, 'rb') as f:
    blkPos = np.reshape(np.fromfile(f, 'f4', count = 2*nblock), (2,nblock))
# read block neighbor id
with open(nabaBlk_file,'rb') as f:
    nNearNabaBlk = np.fromfile(f, 'u4', count = nblock)
    nNabaBlk = np.fromfile(f, 'u4', count = nblock)
    nabaBlkId = np.empty(nblock,dtype=object)
    print(nNabaBlk)
    for i in range(nblock):
        nabaBlkId[i] = np.fromfile(f, 'u4', count = nNabaBlk[i])            
    print('nNearNeighborBlock:')
    print(f'[{np.min(nNearNabaBlk)}, {np.mean(nNearNabaBlk)},{np.max(nNearNabaBlk)}]')
    print('nNeighborBlock:')
    print(f'[{np.min(nNabaBlk)}, {np.mean(nNabaBlk)},{np.max(nNabaBlk)}]')

print(conMat_file)
with open(conMat_file, 'rb') as f:
    nearNeighborBlock = np.fromfile(f, 'u4', count=1)[0]
    conMat = np.reshape(np.fromfile(f, 'f4', count = networkSize*nearNeighborBlock*blockSize),(nblock, nearNeighborBlock, blockSize, blockSize)) # pre, post
    print(f'connection strength (only for connected pairs), min, mean, max: {np.min(conMat[conMat>0])}, {np.mean(conMat[conMat>0])}, {np.max(conMat[conMat>0])}')

with open(delayMat_file, 'rb') as f:
    nearNeighborBlock = np.fromfile(f, 'u4', count=1)[0]
    delayMat = np.reshape(np.fromfile(f, 'f4', count = networkSize*nearNeighborBlock*blockSize),(nblock, nearNeighborBlock, blockSize, blockSize)) # pre, post
    print(f'delays: {np.min(delayMat)}, {np.mean(delayMat)}, {np.max(delayMat)} ms')
    
with open(vec_file, 'rb') as f:
    connectLongRange = np.fromfile(f, 'i4', count = 1)[0]
    print(f'connectLongRange = {connectLongRange}')
    nTotalVec = np.fromfile(f, 'u4', count = networkSize)
    if connectLongRange == 1:
        nVec = np.fromfile(f, 'u4', count = networkSize)
        longRange_nVec = nTotalVec - nVec
        print(f'number of long-range connections outside block: {np.min(longRange_nVec[longRange_nVec>0])}, {np.mean(longRange_nVec)}, {np.max(longRange_nVec)}')
    else:
        nVec = nTotalVec
        longRange_nVec = np.zeros(networkSize, dtype = int)
        print(f'no long-range connections made')
    print(f'number of near-range connections outside block: {np.min(nVec)}, {np.mean(nVec)}, {np.max(nVec)}')
    vecID = np.empty(networkSize, dtype=object)
    conVec = np.empty(networkSize, dtype=object)
    delayVec = np.empty(networkSize, dtype=object)
    for i in range(networkSize):
        if nTotalVec[i] > 0:
            vecID[i] = np.fromfile(f, 'u4', count = nTotalVec[i])
            conVec[i] = np.fromfile(f, 'f4', count = nTotalVec[i])
            delayVec[i] = np.fromfile(f, 'f4', count = nTotalVec[i])
        else:
            vecID[i] = np.array([])
            conVec[i] = np.array([])
            delayVec[i] = np.array([])

if connectLongRange:
    with open(connectomeFn, 'rb') as f:
        f.seek(-2*4, 2)
        longRangeLOI, longRangeSOI = np.fromfile(f, 'f4', 2)
        print(f'longRangeROI: {(longRangeSOI, longRangeLOI)}')

max_str = np.zeros((networkSize, 2))
for ib in range(nblock):
    for jType in range(2):
        if jType == 0:
            max_str[ib*blockSize:(ib+1)*blockSize, jType] = np.max(np.vstack(conMat[ib,:nNearNabaBlk[ib], :typeAcc[nTypeE], :]), axis = 0)
        else:
            max_str[ib*blockSize:(ib+1)*blockSize, jType] = np.max(np.vstack(conMat[ib,:nNearNabaBlk[ib], typeAcc[nTypeE]:typeAcc[nType], :]), axis = 0)

        vec_max = np.zeros(blockSize, dtype = int)
        for j in range(ib*blockSize, (ib+1)*blockSize):
            if nTotalVec[j] > 0:
                if jType == 0:
                    pick = vecID[j] % blockSize < typeAcc[nTypeE]
                else:
                    pick = vecID[j] % blockSize >= typeAcc[nTypeE]
                if pick.any():
                    vec_max[j - ib*blockSize] = np.max(conVec[j][pick])

        max_str[ib*blockSize:(ib+1)*blockSize, jType] = np.max(np.vstack((max_str[ib*blockSize:(ib+1)*blockSize, jType], vec_max)), axis = 0)
print(f'max connections strengths: {[np.min(max_str), np.mean(max_str), np.max(max_str)]}')

with open(LGN_V1_ID_file, 'rb') as f:
    nList = np.fromfile(f,'u4',1)[0]
    LGN_V1_ID = np.empty(nList, dtype = object)
    nLGN_V1 = np.zeros(nList, dtype = int)
    assert(nList == networkSize)
    for i in range(nList):
        nLGN_V1[i] = np.fromfile(f, 'u4', 1)[0]
        LGN_V1_ID[i] = np.fromfile(f, 'u4', nLGN_V1[i])

with open(LGN_V1_s_file, 'rb') as f:
    LGN_V1_s = np.empty(nList, dtype = object)
    nList = np.fromfile(f, 'u4', 1)[0]
    maxList = np.fromfile(f, 'u4', 1)[0]
    assert(nList == networkSize)
    for i in range(nList):
        listSize = np.fromfile(f, 'u4', 1)[0]
        assert(nLGN_V1[i] == listSize)
        assert(listSize <= maxList)
        LGN_V1_s[i] = np.fromfile(f, 'f4', listSize)

with open(LGN_vposFn, 'rb') as f:
    nLGN_I = np.fromfile(f, 'u4', 1)[0]
    nLGN_C = np.fromfile(f, 'u4', 1)[0]
    nLGN = nLGN_I + nLGN_C
    max_ecc = np.fromfile(f, 'f4', 1)[0]
    vCoordSpan = np.fromfile(f, 'f4', 4)
    LGN_vpos = np.fromfile(f, 'f4', nLGN*2).reshape(2, nLGN)
    LGN_type = np.fromfile(f, 'u4', nLGN).reshape(nLGN)

    print(f'LGN_x:{[np.min(LGN_vpos[0,:]), np.max(LGN_vpos[0,:])]}')
    print(f'LGN_y:{[np.min(LGN_vpos[1,:]), np.max(LGN_vpos[1,:])]}')
    
epick = np.hstack([j*blockSize + np.arange(typeAcc[0],typeAcc[1]) for j in range(nblock)])
ipick = np.hstack([j*blockSize + np.arange(typeAcc[1],typeAcc[2]) for j in range(nblock)])

with open(featureFn, 'rb') as f:
    nFeature = np.fromfile(f, 'u4', count = 1)[0]
    # add simple complex as a pseudo feature
    feature = np.empty((nFeature+1, networkSize), dtype = 'f4')
    feature[:-1,:] = np.fromfile(f,'f4', count = networkSize*nFeature).reshape(nFeature, networkSize)

nFeature = nFeature + 1
feature[-1,:] = nLGN_V1 > compThres

maxFeature = np.max(feature, axis = -1)
minFeature = np.min(feature, axis = -1)
LR = feature[0,:]
print(f'LR0: {[minFeature[0], maxFeature[0]]}')
print(f'OP0: {[minFeature[1], maxFeature[1]]}')
featureType = np.array([0,1,2])
minFeature[0] = -1
maxFeature[0] = 1
minFeature[1] = 0
maxFeature[1] = 1
minFeature[2] = 0
maxFeature[2] = 1
print(f'LR: {[minFeature[0], maxFeature[0]]}')
print(f'OP: {[minFeature[1], maxFeature[1]]}')
rangeFeature = maxFeature - minFeature
for i in range(nFeature):
    if featureType[i] == 1:
        rangeFeature[i] = rangeFeature[i]/2
assert(featureType.size == nFeature)
def linear_diff(v0, vs):
    return v0-vs
def circular_diff(v0, vs, minv, maxv):
    v_diff = v0 - vs
    v_range = maxv - minv
    pick = v_diff > v_range/2
    v_diff[pick] = v_diff[pick] - v_range  

    pick = v_diff <- v_range/2
    v_diff[pick] = v_diff[pick] + v_range  
    return v_diff

if 'sample' not in locals():
    nType0 = nType
    nType = 1
    sample = np.zeros(ns*nType, dtype = int)
    #i = 0
    #for iblock in np.random.choice(np.arange(nblock), size = ns, replace = False):
    #    for iType in range(nType): 
    #        sample[i] = iblock*blockSize + np.random.randint(typeAcc[iType],typeAcc[iType+1])
    #        i = i + 1
    mid_blocks = np.arange(nblock)
    mid_idx = np.empty(nType, dtype = object)
    for j in range(nType):
        mid_idx[j] = np.hstack([np.arange(i*blockSize + typeAcc[j], i*blockSize + typeAcc[j+1]) for i in mid_blocks])
    for i in range(ns):
        for j in range(nType):
            sample[nType*i + j] = np.random.choice(mid_idx[j][np.logical_and(feature[1,mid_idx[j]] >= i/ns, feature[1,mid_idx[j]] < (i+1)/ns)], 1)
    nType = nType0

else:
    ns = sample.size

with open(stats_file, 'rb') as f:
    nType = np.fromfile(f, 'u4', count=1)[0]
    networkSize = np.fromfile(f, 'u4', count=1)[0]
    ExcRatio = np.fromfile(f, 'f4', count=networkSize)
    connected = np.reshape(np.fromfile(f, 'u4', count=nType*networkSize), (nType, networkSize))
    avail = np.reshape(np.fromfile(f, 'u4', count=nType*networkSize), (nType, networkSize))
    strength = np.reshape(np.fromfile(f, 'f4', count=nType*networkSize), (nType, networkSize))
assert(len(mk) == nType)

if plotLGNsSum or plotLGN_V1_ratio or plot_nLGN_OS:
    lgnData = np.array([np.sum(sArray) for sArray in LGN_V1_s])

if plot_nLGN_OS:
    nrow = 6
    nOri = 6
    fig = plt.figure('preset-OS_dist', figsize = (6,2*nrow))
    iPref = feature[1,:]*180 # for ori
    for i in range(nrow):
        opEdges = (np.arange(nOri+1)-0.5)/nOri*180
        ax = fig.add_subplot(nrow,2,2*i+1)
        ax.hist(iPref[epick], bins=opEdges)
        ax = fig.add_subplot(nrow,2,2*i+2)
        ax.hist(iPref[ipick], bins=opEdges)
        nOri *= 2
    fig.savefig(res_fdr + 'preset-OS_dist' + res_suffix + '.png', dpi = 150)
    plt.close(fig)
    fig = plt.figure('preset-OS_dist_T', figsize = (6,2*nrow))
    iPref = np.mod(feature[1,:]+0.5,1.0)*180 # for ori
    for i in range(nrow):
        opEdges = (np.arange(nOri+1)-0.5)/nOri*180
        ax = fig.add_subplot(nrow,2,2*i+1)
        ax.hist(iPref[epick], bins=opEdges)
        ax = fig.add_subplot(nrow,2,2*i+2)
        ax.hist(iPref[ipick], bins=opEdges)
        nOri *= 2
    fig.savefig(res_fdr + 'preset-OS_dist_T' + res_suffix + '.png', dpi = 150)
    plt.close(fig)
         

    iPref = np.mod(feature[1,:] + 0.5, 1.0)*180 # for ori
    nOri = 6
    opEdges = (np.arange(nOri+1)-0.5)/nOri*180
    fig = plt.figure('nLGN-OS_dist0', figsize = (11,5+maxList))
    ax = fig.add_subplot(2+maxList,4,(1,5))
    target = nLGN_V1[epick]
    ytarget = iPref[epick]
    HeatMap(target, ytarget, np.arange(maxList)+1, opEdges, ax, 'Reds', log_scale = False)
    ax.set_ylabel(f'preset OP')
    ax.set_title(f'#LGN of E')
    ax = fig.add_subplot(2+maxList,4,(2,6))
    target = nLGN_V1[ipick]
    ytarget = iPref[ipick]
    HeatMap(target, ytarget, np.arange(maxList)+1, opEdges, ax, 'Blues', log_scale = False)
    ax.set_title(f'#LGN of I')
    maxLGN_s = np.max(lgnData[epick])
    ax = fig.add_subplot(2+maxList,4,(3,7))
    target = lgnData[epick]
    ytarget = iPref[epick]
    HeatMap(target, ytarget, np.linspace(0, maxLGN_s, nOri), opEdges, ax, 'Reds', log_scale = False)
    ax.set_title(f'sum(LGN_s) of E')
    ax = fig.add_subplot(2+maxList,4,(4,8))
    target = lgnData[ipick]
    ytarget = iPref[ipick]
    HeatMap(target, ytarget, np.linspace(0, maxLGN_s, nOri), opEdges, ax, 'Blues', log_scale = False)
    ax.set_title(f'sum(LGN_s) of I')
    for i in range(maxList):
        ax = fig.add_subplot(2+maxList,4,8 + 4*i+1)
        pick = epick[nLGN_V1[epick] == i]
        if pick.size > 0:
            ytarget = iPref[pick]
            ax.hist(ytarget, bins=opEdges)
        ax.set_ylabel(f'#LGN = {i}')  
        ax = fig.add_subplot(2+maxList,4,8 + 4*i+2)
        pick = ipick[nLGN_V1[ipick] == i]
        if pick.size > 0:
            ytarget = iPref[pick]
            ax.hist(ytarget, bins=opEdges)
        if i > 0:
            ax = fig.add_subplot(2+maxList,4,8 + 4*i+3)
            pick = epick[nLGN_V1[epick] == i]
            if pick.size > 0:
                ytarget = iPref[pick]
                ax.hist(ytarget, bins=opEdges, weights=lgnData[pick]/np.mean(lgnData[pick]))
            ax = fig.add_subplot(2+maxList,4,8 + 4*i+4)
            pick = ipick[nLGN_V1[ipick] == i]
            if pick.size > 0:
                ytarget = iPref[pick]
                ax.hist(ytarget, bins=opEdges, weights=lgnData[pick]/np.mean(lgnData[pick]))
        else:
            ax = fig.add_subplot(2+maxList,4,8 + 4*i+3)
            ytarget = iPref[epick]
            ax.hist(ytarget, bins=opEdges, weights=lgnData[epick]/np.mean(lgnData[epick]))
            ax.set_title(f'for all nLGN>0')
            ax = fig.add_subplot(2+maxList,4,8 + 4*i+4)
            pick = ipick[nLGN_V1[ipick] == i]
            ytarget = iPref[ipick]
            ax.hist(ytarget, bins=opEdges, weights=lgnData[ipick]/np.mean(lgnData[ipick]))
            ax.set_title(f'for all nLGN>0')


    fig.savefig(setup_fdr + 'nLGN-OS_dist0' + conV1_suffix + '.png', dpi = 150)
    plt.close(fig)

iPref = np.mod(feature[1,:] + 0.5, 1.0)*180 # for ori

if plotLGNsSum:
    fig = plt.figure('LGNsSum', dpi = 300)
    ax = fig.add_subplot(121)
    ax.hist(lgnData[LR>0], color = 'r', alpha = 0.5, label = 'R')
    ax.hist(lgnData[LR<0], color = 'b', alpha = 0.5, label = 'L')
    ax.set_title('LR')
    ax = fig.add_subplot(122)
    ax.hist(lgnData[epick], color = 'r', alpha = 0.5, label = 'R')
    ax.hist(lgnData[ipick], color = 'b', alpha = 0.5, label = 'L')
    ax.set_title('EI')
    fig.savefig(setup_fdr + 'LGNsSum' + conLGN_suffix + '.png')
    plt.close(fig)

if plotBlockWiseComplexDist:
    fig = plt.figure('blockComp', dpi = 300)
    ax = fig.add_subplot(121)
    pick = epick[nLGN_V1[epick] == 0]
    ax.hist(pick//blockSize, bins = np.arange(nblock+1), color = 'r', alpha = 0.5, label = 'Exc.C')
    pick = ipick[nLGN_V1[ipick] == 0]
    ax.hist(pick//blockSize, bins = np.arange(nblock+1), color = 'b', alpha = 0.5, label = 'Inh.C')
    ax.legend()
    fig.savefig(setup_fdr + 'blockComp' + conLGN_suffix + '.png')
    plt.close(fig)

if plotLGN_V1_ratio:
    fig = plt.figure('LGN_V1_ratio', dpi = 300)
    grid = gs.GridSpec(2,nType, figure = fig, hspace = 0.2)
    ax0 = fig.add_subplot(grid[0,0])
    ax1 = fig.add_subplot(grid[0,1])
    ax2 = fig.add_subplot(grid[1,0])
    ax3 = fig.add_subplot(grid[1,1])
    mk1 = ['*r', '*b']
    max_nLGN = np.max(nLGN_V1)
    for i in range(nType):
        typeID = np.hstack([j*blockSize + np.arange(typeAcc[i],typeAcc[i+1]) for j in range(nblock)])
        #vData = conVec[typeID]
        #vid = vecID[typeID]
        #vDataSum = np.zeros(typeID.size)
        #for j in range(typeID.size):
        #    assert(vData[j].size == vid[j].size)
        #    if vData[j].size>0:
        #        left = np.mod(vid[j],blockSize)>=typeAcc[0]
        #        right = np.mod(vid[j],blockSize)<typeAcc[1]
        #        vidPick = np.logical_and(left, right)
        #        vDataSum[j] = np.sum(vData[j][vidPick])

        #mData = conMat[:,:,typeAcc[0]:typeAcc[1], typeAcc[i]:typeAcc[i+1]].reshape(nblock,nearNeighborBlock*(typeAcc[1]-typeAcc[0]), typeAcc[i+1]-typeAcc[i])
        #mDataSum = np.sum(mData, axis=1).flatten()

        #v1Data = (mDataSum + vDataSum)
        v1Data = strength[0,typeID] # exc only
        ax1.plot(lgnData[typeID]*sRatioLGN[i], v1Data*sRatioV1, mk1[i], ms = 2.5, label = f'preType_{i}')
        ax1.set_ylabel('V1')
        ax1.set_xlabel('LGN')
        ax1.set_ylim(bottom = 0)
        ax1.set_xlim(left = 0)
        ax1.legend()
        #ax2.hist(lgnData[typeID]*sRatioLGN[i] + v1Data*sRatioV1, bins = max_nLGN+1, label = f'type_{i}', alpha = 0.5)
        ax2.plot(lgnData[typeID]*sRatioLGN[i], lgnData[typeID]*sRatioLGN[i] + v1Data*sRatioV1, mk1[i], ms = 2.5, label = f'type_{i}', alpha = 0.5)
        ax2.legend()
        ax2.set_xlabel('total Exc')
        ax2.set_xlabel('LGN Exc')
        ax3.hist(v1Data*sRatioV1, bins = 20, range = (0, max(v1Data*sRatioV1)), label = f'type_{i}_cort', alpha = 0.5)
        ax3.hist(lgnData[typeID]*sRatioLGN[i], bins = 20, range = (0, max(v1Data*sRatioV1)), label = f'type_{i}_LGN', alpha = 0.5)
        ax3.legend()
        ax3.set_xlabel('Exc')
        ax0.hist(lgnData[typeID]*sRatioLGN[i], bins = np.arange(max_nLGN+1), label = f'type_{i}', alpha = 0.5)
        ax0.legend()
        ax0.set_xlabel('lgn Exc')
    fig.savefig(fig_fdr + 'LGN_V1_ratio' + conLGN_suffix + conV1_suffix + '.png')
    plt.close(fig)
    
if plotPos:
    fig = plt.figure('pos', dpi = 900)
    ax = fig.add_subplot(111)
    for i in range(nblock):
        plt.scatter(pos[i,0,:], pos[i,1,:], s = 0.24, marker = '.', edgecolors = 'none')
        plt.plot(blkPos[0,i], blkPos[1,i], '*r', ms = 1)
    
    for i in range(nblock):
        if i in sampleBlockId:
            for j in range(nNabaBlk[i]):
                if j < nNearNabaBlk[i]:
                    plt.plot(blkPos[0,nabaBlkId[i][j]], blkPos[1,nabaBlkId[i][j]], 'db', ms = 0.2)
                else:
                    plt.plot(blkPos[0,nabaBlkId[i][j]], blkPos[1,nabaBlkId[i][j]], 'sk', ms = 0.2)

    ax.set_aspect('equal')
    fig.savefig(setup_fdr + 'V1_pos' + conV1_suffix + '.png')
    plt.close(fig)
    
if plotStats:
    fig = plt.figure('conStatsSum', dpi = 300)
    grid = gs.GridSpec(nType, 3, figure = fig, hspace = 0.2)
    for i in range(nType):
        typeID = np.hstack([j*blockSize + np.arange(typeAcc[i],typeAcc[i+1]) for j in range(nblock)])
        data1 = connected[:,typeID]
        data2 = avail[:,typeID]
        data3 = strength[:,typeID]
        ax1 = fig.add_subplot(grid[i,0])
        ax2 = fig.add_subplot(grid[i,1])
        ax3 = fig.add_subplot(grid[i,2])
        if i == 0:
            ax1.set_title('connected')
            ax2.set_title('avail')
            ax3.set_title('total str')
        ax1.set_ylabel(f'postType_{i}')
        for j in range(nType):
            zeros = np.nonzero(data1[j,:]==0)[0]
            zeros0 = typeID[zeros]
            print(f'pre{j}, post{i}: min_s:{np.min(data3[j,:]):.3f} over min#:{np.min(data1[j,:])}, 0s{[(id//blockSize, np.mod(id,blockSize)) for id in zeros0]}, max_s:{np.max(data3[j,:]):.3f} over max#:{np.max(data1[j,:])}')
            #count, edges = np.histogram(data1[j,:], bins = 10)
            #x = (edges[:-1] + edges[1:])/2
            #ax1.plot(x, count, '-*', label = f'preType_{j}')
            #ax1.legend()
            ax1.hist(data1[j,:], bins = 10, label = f'preType_{j}')
    
            #count, edges = np.histogram(data2[j,:], bins = 10)
            #x = (edges[:-1] + edges[1:])/2
            #ax2.plot(x, count, '-*', label = f'preType_{j}')
            ax2.hist(data2[j,:], bins = 10, label = f'preType_{j}')
            #ax2.legend()
    
            #count, edges = np.histogram(data3[j,:], bins = 10)
            #x = (edges[:-1] + edges[1:])/2
            #ax3.plot(x, count, '-*', label = f'preType_{j}')
            ax3.hist(data3[j,:], bins = 10, label = f'preType_{j}')
            if i==nType-1:
                ax3.legend(loc='upper right')
    fig.savefig(fig_fdr+'conStatsSum'+conV1_suffix+'.png')
    plt.close(fig)

    fig = plt.figure('conStrPooled', dpi = 300)
    grid = gs.GridSpec(nType, 1, figure = fig, hspace = 0.2)
    for i in range(nType):
        ax = fig.add_subplot(grid[i])
        if i == 0:
            ax.set_title('strength dist.')
        ax.set_ylabel(f'postType_{i}')
        typeID = np.hstack([j*blockSize + np.arange(typeAcc[i],typeAcc[i+1]) for j in range(nblock)])
        vid = np.hstack(vecID[typeID])
        vdata0 = np.hstack(conVec[typeID])
        for j in range(nType):
            mdata = conMat[:,:,typeAcc[j]:typeAcc[j+1],typeAcc[i]:typeAcc[i+1]].flatten() 
            if vid.size > 0:
                preTypeID = np.logical_and(np.mod(vid,blockSize)>=typeAcc[j], np.mod(vid,blockSize)<typeAcc[j+1])
                vdata = vdata0[preTypeID]
            else:
                vdata = np.array([])
            data = np.hstack((mdata[mdata>0], vdata))
            ax.hist(data, bins = 10, log = True, label = f'preType_{j}')
            ax.set_yscale('log')
            #ax.set_xscale('log')

            if i==nType-1:
                ax.legend(loc='upper right')
    fig.savefig(fig_fdr+'conStatsPooled'+conV1_suffix+'.png')
    plt.close(fig)

if plotLGN_V1_sample:
    fig = plt.figure('LGN_V1-sample', dpi = 300)
    grid = gs.GridSpec((ns+3)//4, 4, figure = fig, hspace = 0.2)
    markers = ('^r', 'vg', 'og', 'sr', '*k', 'dk')
    ms = 1.5
    for i in range(ns):
        ax = fig.add_subplot(grid[i//4,np.mod(i,4)])
        iV1 = sample[i]
        iLGN_vpos = LGN_vpos[:,LGN_V1_ID[iV1]]
        iLGN_type = LGN_type[LGN_V1_ID[iV1]]
        if LR[iV1] > 0:
            all_pos = LGN_vpos[:,nLGN_I:nLGN]
            all_type = LGN_type[nLGN_I:nLGN]
        else:
            all_pos = LGN_vpos[:,:nLGN_I]
            all_type = LGN_type[:nLGN_I]

        if nLGN_V1[iV1] > 0:
            iLGN_ms = LGN_V1_s[iV1]
            max_s = np.max(iLGN_ms)
            min_s = np.min(iLGN_ms)
            for j in range(len(markers)):
                pick = all_type == j
                ax.plot(all_pos[0,pick], all_pos[1,pick], markers[j], ms = min_s/max_s*ms, mec = None, mew = 0, alpha = 0.6)
            if plotLGNsSize:
                for j in range(nLGN_V1[iV1]):
                    ax.plot(iLGN_vpos[0,j], iLGN_vpos[1,j], markers[iLGN_type[j]], ms = iLGN_ms[j]/max_s*ms, mfc = None, mec = 'k', mew = ms/4)
                x0 = np.average(iLGN_vpos[0,:], weights = iLGN_ms)
                y0 = np.average(iLGN_vpos[1,:], weights = iLGN_ms)
            else:
                for j in range(6):
                    pick = iLGN_type == j
                    ax.plot(iLGN_vpos[0,pick], iLGN_vpos[1,pick], markers[j], ms = 1.0, mfc = None, mec = 'k', mew = ms/4)
                x0 = np.average(iLGN_vpos[0,:])
                y0 = np.average(iLGN_vpos[1,:])

            orient = (feature[1,iV1] - 0.5)*np.pi + np.pi/2
            x = np.array([np.min(iLGN_vpos[0,:]), np.max(iLGN_vpos[0,:])])
            y = np.array([np.min(iLGN_vpos[1,:]), np.max(iLGN_vpos[1,:])])

            if nLGN_V1[iV1] > 1:
                xl = x[1]-x[0]
                yl = y[1]-y[0]
            else:
                xl = LGN_vpos[0,1]-LGN_vpos[0,0]
                yl = LGN_vpos[1,1]-LGN_vpos[1,0]

            ax.set_xlim(left = x[1] - xl*1.1, right = x[0] + xl*1.1)
            ax.set_ylim(bottom = y[1] - yl*1.1, top = y[0] + yl*1.1)

            if np.diff(y)[0] > np.diff(x)[0]:
                x = (y-y0) / np.tan(orient) + x0
            else:
                y = np.tan(orient)*(x-x0) + y0

            ax.plot(x0, y0, '*b')
            ax.plot(x, y, '-k', label = 'preset')
            if i == 0:
                ax.legend()

        ax.set_aspect('equal')
        ax.set_title(f'{orient*180/np.pi:.1f}')

    fig.savefig(fig_fdr+'LGN_V1-sample'+conLGN_suffix+'.png')
    plt.close(fig)

if plotCon_sample:
    red = np.array([0.0, 1, 1])
    blue = np.array([0.666666, 1, 1])
    magenta = np.array([0.8333333, 1, 1])
    green = np.array([0.333333, 1, 0.5])
    ms1 = 0.2
    ms2 = 0.2
    mk1 = '.'
    mk2 = 's'
    lw = 0.1
    sat0 = 0.3
    sat1 = 1.0
    #sat_pick = 1.0

    pos0 = np.zeros((2,networkSize))
    pos0[0,:] = pos[:,0,:].reshape(networkSize)
    pos0[1,:] = pos[:,1,:].reshape(networkSize)

    mSize = 0.15
    alpha0 = 0.65
    alpha1 = 0.9
    for i in sample:
        fig = plt.figure('V1_con-'+f'{i}', dpi = 2000)
        ax = fig.add_subplot(111)
        # background map
        pick = epick[LR[epick] > 0]
        nnE = pick.size

        color = np.tile(np.array([0,0,1], dtype = float), (nnE,1))
        color[:,1] = sat0
        color[:,0] = feature[1,pick]
        ax.scatter(pos0[0,pick], pos0[1,pick], s = ms2, c = clr.hsv_to_rgb(color), edgecolors = 'none', marker = mk2, alpha = alpha0)

        pick = ipick[LR[ipick] > 0]
        nnI = pick.size

        color = np.tile(np.array([0,0,1], dtype = float), (nnI,1))
        color[:,1] = sat0
        color[:,0] = feature[1,pick]
        ax.scatter(pos0[0,pick], pos0[1,pick], s = ms2, c = clr.hsv_to_rgb(color), edgecolors = 'none', marker = mk2, alpha = alpha0)

        pick = epick[LR[epick] < 0]
        nnE = pick.size

        color = np.tile(np.array([0,0,1], dtype = float), (nnE,1))
        color[:,1] = sat1
        color[:,0] = feature[1,pick]
        ax.scatter(pos0[0,pick], pos0[1,pick], s = ms1, c = clr.hsv_to_rgb(color), edgecolors = 'none', marker = mk2, alpha = alpha0)

        pick = ipick[LR[ipick] < 0]
        nnI = pick.size

        color = np.tile(np.array([0,0,1], dtype = float), (nnI,1))
        color[:,1] = sat1
        color[:,0] = feature[1,pick]
        ax.scatter(pos0[0,pick], pos0[1,pick], s = ms1, c = clr.hsv_to_rgb(color), edgecolors = 'none', marker = mk2, alpha = alpha0)

        # post
        bid = i//blockSize
        tid = i-blockSize*bid
        # pre within the blocks nearby
        for j in range(nNearNabaBlk[bid]):
            jbid = nabaBlkId[bid][j]

            if j == 0:
                marker = 'v' # inside own block
            else:
                marker = 's' # outside
            mat_pick = conMat[bid,j,:,tid]>0
            matE_pick = mat_pick.copy()
            matI_pick = mat_pick.copy()
            matE_pick[typeAcc[nTypeE]:typeAcc[nType]] = False
            matI_pick[:typeAcc[nTypeE]] = False

            msE_size = conMat[bid,j,matE_pick,tid]
            msI_size = conMat[bid,j,matI_pick,tid]

            if msE_size.size > 0:
                ax.scatter(pos[jbid,0,matE_pick], pos[jbid,1,matE_pick], s = mSize*msE_size/max_str[i, 0], marker = marker, facecolor = None, edgecolor = 'r', linewidths = lw, alpha = alpha1)
                #ax.plot(pos[jbid,0,matE_pick], pos[jbid,1,matE_pick], marker, mec='r', mfc = None, ms = ms1*1.1)
            if msI_size.size > 0:
                ax.scatter(pos[jbid,0,matI_pick], pos[jbid,1,matI_pick], s = mSize*msI_size/max_str[i, 1], marker = marker, facecolor = None, edgecolor = 'b', linewidths = lw, alpha = alpha1)
                #ax.plot(pos[jbid,0,matI_pick], pos[jbid,1,matI_pick], marker, mec='b', mfc = None, ms = ms1*1.1)

        if nTotalVec[i] > 0:
            vID = vecID[i][: nVec[i]]
            cStr = conVec[i][: nVec[i]]
            # far pre 
            # exc
            LE_pick = vID % blockSize < typeAcc[nTypeE]
            if LE_pick.any():
                vbid = vID[LE_pick]//blockSize
                vtid = vID[LE_pick] - blockSize*vbid
                msE_size = cStr[LE_pick]
                ax.scatter(pos[vbid,0,vtid], pos[vbid,1,vtid], s = mSize*msE_size/max_str[i, 0], marker = 'd', facecolor = None, edgecolor = 'r', linewidths = lw, alpha = alpha1)

            # inh 
            LI_pick = vID % blockSize >= typeAcc[nTypeE]
            if LI_pick.any():
                vbid = vID[LI_pick]//blockSize
                vtid = vID[LI_pick] - blockSize*vbid
                msI_size = cStr[LI_pick]
                ax.scatter(pos[vbid,0,vtid], pos[vbid,1,vtid], s = mSize*msI_size/max_str[i, 1], marker = 'd', facecolor = None, edgecolor = 'b', linewidths = lw, alpha = alpha1)

        if longRange_nVec[i] > 0:
            vID = vecID[i][nVec[i]:]
            cStr = conVec[i][nVec[i]:]
            # pre outside the block
            # exc
            LE_pick = vID % blockSize < typeAcc[nTypeE]
            if LE_pick.any():
                vbid = vID[LE_pick]//blockSize
                vtid = vID[LE_pick] - blockSize*vbid
                msE_size = cStr[LE_pick]
                ax.scatter(pos[vbid,0,vtid], pos[vbid,1,vtid], s = mSize*msE_size/max_str[i, 0], marker = '^', facecolor = None, edgecolor = 'm', linewidths = lw, alpha = alpha1)

            # inh 
            LI_pick = vID % blockSize >= typeAcc[nTypeE]
            if LI_pick.any():
                vbid = vID[LI_pick]//blockSize
                vtid = vID[LI_pick] - blockSize*vbid
                msI_size = cStr[LI_pick]
                ax.scatter(pos[vbid,0,vtid], pos[vbid,1,vtid], s = mSize*msI_size/max_str[i, 1], marker = '^', facecolor = None, edgecolor = 'c', linewidths = lw, alpha = alpha1)

        ax.plot(pos[bid,0,tid], pos[bid,1,tid],'*k', mfc = None, mew = 0.05, ms = 1, alpha = alpha1)
        
        ax.set_aspect('equal')
        ax.set_title(f'neuron {bid}-{tid} preset to {iPref[i]:.0f} deg')
        fig.savefig(fig_fdr+'V1_conSample-'+f'{bid}-{tid}' + conV1_suffix + '.png')
        plt.close(fig)

if plotConFeature_stats:
    feat = ('LR', 'OP', 'CS')
    archType = ('E', 'I')
    bins = [25,25,25]
    fig = plt.figure('conFeature-dist', dpi = 300)
    grid = gs.GridSpec(nFeature, nType, figure = fig)
    for iType in range(nType):
        pick = np.hstack([j*blockSize + np.arange(typeAcc[iType],typeAcc[iType+1]) for j in range(nblock)]) 
        for iF in range(nFeature):
            ax = fig.add_subplot(grid[iF, iType])
            ax.hist(feature[iF, pick], bins = bins[iF])
    fig.savefig(fig_fdr+'conFeature-dist' + conV1_suffix + '.png')
    plt.close(fig)

    cm = ('Reds', 'Blues')
    ranges = (np.array([-1,1]), np.array([0.0, 1.0]), np.array([0.0, 1.0]))
    #mRanges = (np.array([-2,2]), np.array([-0.5, 0.5]))
    mRanges = (30,30,30)
    stdBins = (25,25,25)
    logScale = False 
    tickPick = (np.array([0,0.5,1.0]), np.array([0,0.25,0.5,0.75,1.0]), np.array([0,0.5,1.0]))
    for iType in range(nType):
        fig = plt.figure(f'conFeature-{archType[iType]}', figsize = np.array([nFeature*2, nFeature*nType])*4 ,dpi = 300)
        grid = gs.GridSpec(nFeature*nType, nFeature*2, figure = fig, hspace = 0.5, wspace = 0.5)
        for iF in range(nFeature): # ipost
            xFeature = feature[iF, np.hstack([j*blockSize + np.arange(typeAcc[iType],typeAcc[iType+1]) for j in range(nblock)])]
            for jF in range(nFeature): #jpre
                if jF == 1:
                    def diff(v0, vs):
                        return circular_diff(v0, vs, minFeature[jF], maxFeature[jF])
                else:
                    def diff(v0, vs):
                        return linear_diff(v0, vs)
                iTypeN = typeAcc[iType+1]-typeAcc[iType]
                mean_std = np.zeros((2,nType,iTypeN*nblock))
                nCon = np.zeros((nType,iTypeN*nblock))
                for i in range(nblock):
                    ipost = np.array([i*blockSize + tid for tid in range(typeAcc[iType], typeAcc[iType+1])])
                    for j in range(nNearNabaBlk[i]):
                        bid = nabaBlkId[i][j]
                        for jType in range(nType):
                            jTypeN = typeAcc[jType+1]-typeAcc[jType]
                            ipre = np.array([bid*blockSize + tjd for tjd in range(typeAcc[jType], typeAcc[jType+1])])

                            cStr = conMat[i,j, typeAcc[jType]:typeAcc[jType+1], typeAcc[iType]:typeAcc[iType+1]]
                            nCon[jType,i*iTypeN:(i+1)*iTypeN] += np.sum(cStr>0, axis = 0)
                            iFeature = np.tile(feature[jF,ipost], (jTypeN,1))
                            jFeature = np.tile(feature[jF,ipre], (iTypeN,1)).T

                            value = diff(iFeature, jFeature) * cStr
                            mean_std[0,jType,i*iTypeN:(i+1)*iTypeN] += np.sum(value, axis = 0)
                            mean_std[1,jType,i*iTypeN:(i+1)*iTypeN] += np.sum(np.power(value,2), axis = 0)
                
                mean_std[0,:,:] /= nCon
                var = mean_std[1,:,:]/nCon - np.power(mean_std[0,:,:],2)
                pick = var < 0
                var[pick] = 0
                mean_std[1,:,:] = np.sqrt(var)
                mean_std[np.isnan(mean_std)] = 0
                
                for jType in range(nType):
                    igrid = iF*2
                    jgrid = jF*nType + jType
                    ax = fig.add_subplot(grid[jgrid, igrid])
                    HeatMap(xFeature, mean_std[0,jType,:], ranges[iF], mRanges[jF], ax, cm[jType], log_scale = logScale, intPick = False, tickPick1 = tickPick[iF])
                    ax.set_title(f'mean of {feat[iF]}<-{feat[jF]}, {archType[iType]}<-{archType[jType]}')
                    ax.set_xlabel(f'{feat[iF]}')
                    ax.set_ylabel(f'diff {feat[jF]}')
                    ax = fig.add_subplot(grid[jgrid, igrid+1])
                    HeatMap(xFeature, mean_std[1,jType,:], ranges[iF], stdBins[jF], ax, cm[jType], log_scale = logScale, intPick = False, tickPick1 = tickPick[iF])
                    ax.set_title('std')

        fig.savefig(fig_fdr+f'conFeature-{archType[iType]}'+ conV1_suffix + '.png')
        plt.close(fig)

if plotConFeature_sample:
    fig = plt.figure('conFeature-sample', figsize = np.array([nFeature*2, ns])*2, dpi = 300)
    grid = gs.GridSpec(ns, nFeature*2, figure = fig, hspace = 0.5, wspace = 0.2)
    for i in range(nFeature):
        if featureType[i] == 0:
            def diff(v0, vs):
                return linear_diff(v0, vs)
        else:
            if featureType[i] == 1:
                def diff(v0, vs):
                    return circular_diff(v0, vs, minFeature[i], maxFeature[i])
        blockRange = np.arange(blockSize)
        for k in range(ns):
            ipost = sample[k]
            for iType in range(nType):
                if typeAcc[iType] <= np.mod(ipost,blockSize) < typeAcc[iType+1]:
                    postType = iType
                    break;
            ax = fig.add_subplot(grid[k,i*2])
            ax2 = fig.add_subplot(grid[k,i*2+1])
            bid = ipost//blockSize
            tid = ipost-blockSize*bid
            # pre within the blocks nearby
            total_diff = np.empty(nType, dtype = object)
            for iType in range(nType):
                total_diff[iType] = []
            for j in range(nNearNabaBlk[bid]):
                jbid = nabaBlkId[bid][j]
                for iType in range(nType):
                    typePick = np.arange(typeAcc[iType],typeAcc[iType+1])
                    mat_pick = conMat[bid,j,typePick,tid]>0
                    pre_id = jbid*blockSize + blockRange[typePick[mat_pick]]
                    m_diff = diff(feature[i,ipost], feature[i,pre_id])
                    npre = pre_id.size
                    color = mpl.colors.hsv_to_rgb(np.stack(((m_diff+rangeFeature[i])/(2*rangeFeature[i]), np.ones(npre), np.ones(npre)), axis = 1))
                    ax.scatter(pos[jbid,0,typePick[mat_pick]], pos[jbid,1,typePick[mat_pick]], s = 0.1, c=color, marker = mk[iType], edgecolors = 'none')
                    total_diff[iType].append(m_diff)
            if nTotalVec[ipost] > 0:
                # pre outside the block
                vbid = vecID[ipost]//blockSize
                vtid = vecID[ipost] - blockSize*vbid
                for iType in range(nType):
                    vTypePick = np.logical_and(vtid < typeAcc[iType+1], vtid >= typeAcc[iType])
                    pre_id = vbid[vTypePick]*blockSize + vtid[vTypePick]
                    m_diff = diff(feature[i,ipost], feature[i,pre_id])
                    npre = pre_id.size
                    color = mpl.colors.hsv_to_rgb(np.stack(((m_diff+rangeFeature[i])/(2*rangeFeature[i]), np.ones(npre), np.ones(npre)), axis = 1))
                    v_diff = diff(feature[i,ipost], feature[i,pre_id])
                    ax.scatter(pos[vbid[vTypePick],0,vtid[vTypePick]], pos[vbid[vTypePick],1,vtid[vTypePick]], s = 0.1, c=color, marker = mk[iType], edgecolors = 'none')
                    total_diff[iType].append(v_diff)
    
            ax.plot(pos[bid,0,tid], pos[bid,1,tid],'*k', ms = 1)
            mean_std = np.empty((2,nType))
            for iType in range(nType):
                temp = np.hstack(total_diff[iType])
                mean_std[0,iType] = np.mean(temp)
                mean_std[1,iType] = np.std(temp)
                ax2.hist(temp, range = (-rangeFeature[i], rangeFeature[i]), label = f'archType{iType}')
            if i==0 and k==0:
                ax2.legend() 
            if k == 0:
                ax.set_title(f'feat{i} pos')
                ax2.set_title(f'feat{i} dist')
            if i==0:
                ax.set_ylabel(f'archType{postType}')
            ax.set_aspect('equal')
            ax2.set_xlabel(f'{mean_std[0,0]:.3f}, {mean_std[1,0]:.3f} | {mean_std[0,1]:.3f}, {mean_std[1,1]:.3f}')
    
    fig.savefig(setup_fdr + 'conFeature-sample' + conV1_suffix + '.png')
    plt.close(fig)

if plotConFeature_preSynTC:
    feat = ('LR', 'OP', 'CS')
    archType = ('E', 'I')
    bins = ([-1,1,3], np.linspace(0.0, 1.0, 9)-0.5, [-0.5, 0.5, 1.5]) 
    color = np.array([[0,1,1], [0.66666,1,1]])
    percentile = 25
    logScale = False 
    tick = (np.array([0,2]), np.array([0,0.25,0.5,0.75,1.0])-0.5, np.array([0,1]))
    ticklabel = np.array([['Ipsi', 'Contra'], [f'{t*180:.0f}' for t in tick[1]], ['C', 'S']], dtype = object)
    for iType in range(nType): #post
        fig = plt.figure(f'conFeature_preSynTC-{archType[iType]}', figsize = np.array([nFeature, nType])*4 ,dpi = 300)
        grid = gs.GridSpec(nFeature, nType*2, figure = fig, hspace = 0.5, wspace = 0.5)
        for iF in range(nFeature): # ipost
            iTypeN = typeAcc[iType+1]-typeAcc[iType]
            #               preType, preSynaptic
            data = np.empty((nType,iTypeN*nblock), dtype = object)
            longRange_data = np.empty((nType,iTypeN*nblock), dtype = object)
            hasLongRange = np.zeros(nType, dtype = bool)
            for i in range(nType):
                for j in range(iTypeN*nblock):
                    data[i,j] = []
                    longRange_data[i,j] = []
            for i in range(nblock):
                ipost = np.array([i*blockSize + tid for tid in range(typeAcc[iType], typeAcc[iType+1])])
                for j in range(nNearNabaBlk[i]):
                    bid = nabaBlkId[i][j]
                    for jType in range(nType):
                        jTypeN = typeAcc[jType+1]-typeAcc[jType]
                        ipre = np.array([bid*blockSize + tjd for tjd in range(typeAcc[jType], typeAcc[jType+1])])
                        cStr = conMat[i,j, typeAcc[jType]:typeAcc[jType+1], typeAcc[iType]:typeAcc[iType+1]]
                        jFeature = np.tile(feature[iF,ipre], (iTypeN,1)).T
                        if iF == 0:
                            iFeature = np.tile(feature[iF,ipost], (jTypeN,1))
                            value = np.abs(jFeature - iFeature)
                        if iF == 1:
                            iFeature = np.tile(feature[iF,ipost], (jTypeN,1))
                            value = circular_diff(iFeature, jFeature, minFeature[iF], maxFeature[iF])
                        if iF == 2:
                            value = jFeature
                        for iq in range(iTypeN):
                            weight = cStr[cStr[:,iq]>0, iq]
                            data[jType,i*iTypeN+iq].extend(value[cStr[:,iq] > 0,iq]*weight)
                iq = 0
                for j in ipost:
                    if nVec[j] > 0:
                        ipre = vecID[j][:nVec[j]]
                        cStr = conVec[j][:nVec[j]]
                        jFeature = feature[iF,ipre]
                        if iF == 0:
                            value = np.abs(jFeature - feature[iF,j])
                        if iF == 1:
                            value = circular_diff(feature[iF,j], jFeature, minFeature[iF], maxFeature[iF])
                        if iF == 2:
                            value = jFeature
                        for jType in range(nType):
                            pick = np.logical_and(ipre % blockSize >= typeAcc[jType], ipre % blockSize < typeAcc[jType+1])
                            if pick.any():
                                weight = cStr[pick]
                                data[jType, i*iTypeN + iq].extend(value[pick]*weight)

                    if longRange_nVec[j] > 0:
                        ipre = vecID[j][nVec[j]:]
                        cStr = conVec[j][nVec[j]:]
                        jFeature = feature[iF,ipre]
                        if iF == 0:
                            value = np.abs(jFeature - feature[iF,j])
                        if iF == 1:
                            value = circular_diff(feature[iF,j], jFeature, minFeature[iF], maxFeature[iF])
                        if iF == 2:
                            value = jFeature
                        for jType in range(nType):
                            pick = np.logical_and(ipre % blockSize >= typeAcc[jType], ipre % blockSize < typeAcc[jType+1])
                            if pick.any():
                                weight = cStr[pick]
                                longRange_data[jType, i*iTypeN + iq].extend(value[pick]*weight)
                                hasLongRange[jType] = True
                    iq += 1
            
            for i in range(nType):
                for j in range(iTypeN*nblock):
                    data[i,j] = np.array([data[i,j]])
                    longRange_data[i,j] = np.array([longRange_data[i,j]])
            for jType in range(nType):
                ax = fig.add_subplot(grid[iF, jType*2])
                TuningCurves(data[jType,:], bins[iF], percentile, ax, color[jType], tick[iF], ticklabel[iF])
                ax.set_title(f'{archType[iType]}<-{feat[iF]}')

                ax = fig.add_subplot(grid[iF, jType*2+1])
                if hasLongRange[jType]:
                    TuningCurves(longRange_data[jType,:], bins[iF], percentile, ax, color[jType], tick[iF], ticklabel[iF])
                    ax.set_title(f'longRange {archType[iType]}<-{feat[iF]}')
                else:
                    ax.set_title(f'no long-range connection made\n from type {jType} to {iType}')

        fig.savefig(setup_fdr + f'conFeature_preSynTC-{archType[iType]}' + conV1_suffix + '.png')
        plt.close(fig)
