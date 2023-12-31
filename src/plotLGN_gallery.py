#!/usr/bin/env python
# coding: utf-8
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import axes3d
from matplotlib import cm

import sys
if len(sys.argv) < 4:
    print("need suffix, data_fdr, fig_fdr as input")
else:
    suffix = sys.argv[1]
    data_fdr = sys.argv[2]
    fig_fdr = sys.argv[3]

print(suffix)
if suffix:
    suffix = "-" + suffix

if data_fdr[-1] != '/':
    data_fdr += '/'
if fig_fdr[-1] != '/':
    fig_fdr += '/'
#iLGN = np.array([0])
#iLGN = np.array([264, 462])
#iLGN = np.array([267, 11])
iLGN = np.array([6214, 19782])
ns = 1
precision = 'f4'

output = data_fdr+"LGN_gallery" + suffix + ".bin"
with open(output, 'rb') as f:
    nParvo = np.fromfile(f, 'u4', 1)[0]
    nType = np.fromfile(f, 'u4', 1)[0]
    nKernelSample = np.fromfile(f, 'u4', 1)[0]
    nSample = np.fromfile(f, 'u4', 1)[0]
    nMagno = np.fromfile(f, 'u4', 1)[0]
    mType = np.fromfile(f, 'u4', 1)[0]
    assert(mType == 1)
    mKernelSample = np.fromfile(f, 'u4', 1)[0]
    mSample = np.fromfile(f, 'u4', 1)[0]
    nParvo_I = np.fromfile(f, 'u4', 1)[0]
    nParvo_C = np.fromfile(f, 'u4', 1)[0]
    nMagno_I = np.fromfile(f, 'u4', 1)[0]
    nMagno_C = np.fromfile(f, 'u4', 1)[0]
    print(f'parvo:{(nParvo_I, nParvo_C)} {nType} types, magno: {(nMagno_I, nMagno_C)} {mType} types')
    nLGN = nParvo + nMagno
    max_convol = np.fromfile(f, precision, nLGN)
    tw = np.fromfile(f, precision, nParvo*nType*nKernelSample).reshape((nParvo,nType,nKernelSample))
    sw = np.fromfile(f, precision, nSample*(nParvo>0))
    sc = np.fromfile(f, 'f4', 2*nParvo*nType*nSample).reshape((2,nParvo,nType,nSample))
    tw_m = np.fromfile(f, precision, nMagno*mKernelSample).reshape((nMagno,mKernelSample))
    sw_m = np.fromfile(f, precision, nMagno*mSample).reshape((nMagno,mSample))
    sc_m = np.fromfile(f, 'f4', 2*nMagno*mSample).reshape((2,nMagno,mSample))
nSample1D = np.sqrt(nSample).astype(int)
mSample1D = np.sqrt(mSample).astype(int)
print(f'nParvo = {nParvo}, nType = {nType}, nKernelSample = {nKernelSample}, nSample = {nSample}, nSample1D = {nSample1D}')
print(f'nMagno = {nMagno}, mType = {mType}, mKernelSample = {mKernelSample}, mSample = {mSample}, mSample1D = {mSample1D}')

if 'iLGN' not in locals():
    iLGN = np.random.randint(nLGN, size=ns)

output = data_fdr + "LGN" + suffix + ".bin"
with open(output, 'rb') as f:
    nLGN = np.fromfile(f, 'u4', 1)[0]
    LGN_type = np.fromfile(f, 'u4', nLGN)
    LGN_polar = np.fromfile(f, precision, 2*nLGN).reshape(2,nLGN)
    LGN_ecc = np.fromfile(f, precision, 2*nLGN).reshape(2,nLGN)
    LGN_rw = np.fromfile(f, precision, 2*nLGN).reshape(2,nLGN)
    LGN_rh = np.fromfile(f, precision, 2*nLGN).reshape(2,nLGN)
    LGN_orient = np.fromfile(f, precision, 2*nLGN).reshape(2,nLGN)
    LGN_k = np.fromfile(f, precision, 2*nLGN).reshape(2,nLGN)
    LGN_ratio = np.fromfile(f, precision, 2*nLGN).reshape(2,nLGN)
    tau_R = np.fromfile(f, precision, 2*nLGN).reshape(2,nLGN)
    tau_D = np.fromfile(f, precision, 2*nLGN).reshape(2,nLGN)
    nR = np.fromfile(f, precision, 2*nLGN).reshape(2,nLGN)
    nD = np.fromfile(f, precision, 2*nLGN).reshape(2,nLGN)
    delay = np.fromfile(f, precision, 2*nLGN).reshape(2,nLGN)
    spont = np.fromfile(f, precision, nLGN)
    c50 = np.fromfile(f, precision, nLGN)
    sharpness = np.fromfile(f, precision, nLGN)
    coneType = np.fromfile(f, 'u4', 2*nLGN).reshape(2,nLGN)
    covariant = np.fromfile(f, precision, nLGN)

print(f'LGN_type:{np.min(LGN_type)},{np.max(LGN_type)}')

print(f'center: ecc[{np.min(LGN_ecc[0,:])},{np.max(LGN_ecc[0,:])}], polar[{np.min(LGN_polar[0,:])}, {np.max(LGN_polar[0,:])}]')
print(f'center: rh[{np.min(LGN_rh[0,:])}, {np.mean(LGN_rh[0,:])}, {np.max(LGN_rh[0,:])}], rw[{np.min(LGN_rw[0,:])}, {np.mean(LGN_rw[0,:])}, {np.max(LGN_rw[0,:])}]')
print(f'surround: ecc[{np.min(LGN_ecc[1,:])},{np.max(LGN_ecc[1,:])}], polar[{np.min(LGN_polar[1,:])}, {np.max(LGN_polar[1,:])}]')
print(f'surround: rh[{np.min(LGN_rh[1,:])}, {np.mean(LGN_rh[1,:])}, {np.max(LGN_rh[1,:])}], rw[{np.min(LGN_rw[1,:])}, {np.mean(LGN_rw[1,:])}, {np.max(LGN_rw[1,:])}]')

print(f'k[{np.min(LGN_k)},{np.max(LGN_k)}], orient[{np.min(LGN_orient)}, {np.max(LGN_orient)}]')
print(f'ratio[{np.min(LGN_ratio)},{np.max(LGN_ratio)}]')
print(f'tau_R[{np.min(tau_R)},{np.max(tau_R)}], tau_D[{np.min(tau_D)}, {np.max(tau_D)}]')
print(f'nR[{np.min(nR)},{np.max(nR)}], nD[{np.min(nD)}, {np.max(nD)}]')
print(f'delay[{np.min(delay)},{np.max(delay)}], spont[{np.min(spont)}, {np.max(spont)}]')
print(f'c50[{np.min(c50)},{np.max(c50)}], sharpness[{np.min(sharpness)}, {np.max(sharpness)}]')
print(f'coneType[{np.min(coneType)},{np.max(coneType)}]')

print(f'max convol: {[min(max_convol), np.mean(max_convol), max(max_convol)]}')
imax = np.argmax(max_convol)
imin = np.argmin(max_convol)
print(f'LGN_k at minimal max_convol: {[LGN_k[0, imin], LGN_k[1, imin]]}')
print(f'LGN_k at maximal max_convol: {[LGN_k[0, imax], LGN_k[1, imax]]}')

fig = plt.figure('check_coord', dpi = 600)
ax = fig.add_subplot(111)
#for i in range(nLGN):
#    ax.plot(sc[0,i,0,:], sc[1,i,0,:], 'o', ms = 0.001)
#    ax.plot(sc[0,i,1,:], sc[1,i,1,:], '>', ms = 0.001)
if nParvo > 0:
    # surround boundary
    ax.plot(sc[0,:,1,0],                       sc[1,:,1,0], '>b', ms = 0.001)
    ax.plot(sc[0,:,1,nSample1D-1],             sc[1,:,1,nSample1D-1], '>b', ms = 0.001)
    ax.plot(sc[0,:,1,(nSample1D-1)*nSample1D], sc[1,:,1,(nSample1D-1)*nSample1D], '>b', ms = 0.001)
    ax.plot(sc[0,:,1,nSample-1],               sc[1,:,1,nSample-1], '>b', ms = 0.001)
    # center boundary
    ax.plot(sc[0,:,0,0],                       sc[1,:,0,0], 'or', ms = 0.004)
    ax.plot(sc[0,:,0,nSample1D-1],             sc[1,:,0,nSample1D-1], 'or', ms = 0.004)
    ax.plot(sc[0,:,0,(nSample1D-1)*nSample1D], sc[1,:,0,(nSample1D-1)*nSample1D], 'or', ms = 0.004)
    ax.plot(sc[0,:,0,nSample-1],               sc[1,:,0,nSample-1], 'or', ms = 0.004)
if nMagno > 0:
    ax.plot(sc_m[0,:,0],                       sc_m[1,:,0], '*k', ms = 0.001)
    ax.plot(sc_m[0,:,mSample1D-1],             sc_m[1,:,mSample1D-1], '*k', ms = 0.001)
    ax.plot(sc_m[0,:,(mSample1D-1)*mSample1D], sc_m[1,:,(mSample1D-1)*mSample1D], '*k', ms = 0.001)
    ax.plot(sc_m[0,:,mSample-1],               sc_m[1,:,mSample-1], '*k', ms = 0.001)
ax.set_aspect('equal')
fig.savefig(fig_fdr + 'check_coord' + suffix + '.png')

def getSF(rC, rS, kC, kS, cov):
    # rC, rS in rad
    zeroCross = np.sqrt(np.log(np.abs((kC/rC/rC)/(kS*cov/rS/rS)))/(1/rC/rC - 1/rS/rS))
    return 1/(4*zeroCross*180/np.pi) # cycles per degree

def getTF(kC, kS, twC, twS, cov):
    tw = kC*twC + kS*cov*twS

    itw = np.abs(np.argmax(tw) - np.argmin(tw))
    tf = 1000/(2*itw)
    return tf, tw 

def getTF_m(tw):
    itw = np.abs(np.argmax(tw) - np.argmin(tw))
    tf = 1000/(2*itw)
    return tf 

cov_t = np.zeros(nLGN)
for j in range(nLGN):
    cov_t[j] = covariant[j]
    #cov_t[j] = 1
    if j < nParvo_I or (j >= nMagno_I + nParvo_I and j < nMagno_I + nParvo_I + nParvo_C):
        i = j
        if i >= nMagno_I + nParvo_I:
            i = i - nMagno_I
        it = np.argmax(tw[i,0,:])
        cov_t[j] *= tw[i,1,it]/tw[i,0,it]

SF = getSF((LGN_rw[0,:] + LGN_rh[0,:])/2, (LGN_rw[1,:] + LGN_rh[1,:])/2, LGN_k[0,:], LGN_k[1,:], cov_t)

TF = np.zeros(nLGN)
temporal_m = np.zeros((tw_m.shape[1],nMagno))
temporal = np.zeros((tw.shape[2],nParvo))
for j in range(nLGN):
    if j < nParvo_I or (j >= nMagno_I + nParvo_I and j < nMagno_I + nParvo_I + nParvo_C):
        i = j
        if i >= nMagno_I + nParvo_I:
            i = i - nMagno_I
        TF[j], temporal[:,i] = getTF(LGN_k[0,j], LGN_k[1,j], tw[i,0,:], tw[i,1,:], covariant[j])
    else:
        i = j - nParvo_I
        if i >= nMagno_I:
            i = i - nParvo_C
        TF[j] = getTF_m(tw_m[i,:])
        temporal_m[:,i] = tw_m[i,:]


fig = plt.figure('SF-TF', dpi = 600)
ax = fig.add_subplot(221)
ax.hist(SF, bins = 12)
ax.set_xlabel('SF')
ax = fig.add_subplot(222)
ax.hist(TF, bins = 12)
ax.set_xlabel('TF')
# need to be adjusted for parvo and magno
ax = fig.add_subplot(223)
if nParvo > 0:
    ax.plot(np.arange(nKernelSample), temporal, '-g', lw = 0.2)
if nMagno > 0:
    ax.plot(np.arange(mKernelSample), temporal_m, '-b', lw = 0.2)
ax.set_xlabel('t/ms')
fig.savefig(fig_fdr + 'SF-TF' + suffix + '.png')

print(f'SF: {[np.min(SF), np.mean(SF), np.max(SF)]}')
print(f'TF: {[np.min(TF), np.mean(TF), np.max(TF)]}')
print(f'cov: {[np.min(cov_t), np.mean(cov_t), np.max(cov_t)]}')

for j in iLGN:
    print(f'#{j}')
    if j < nParvo_I or (j >= nMagno_I + nParvo_I and j < nMagno_I + nParvo_I + nParvo_C):
        t = np.arange(nKernelSample)
        i = j
        if i >= nMagno_I + nParvo_I:
            i = i - nMagno_I
        assert(i>=0 and i<nParvo)
        fig = plt.figure(f'check_{j}-p{i}-{LGN_type[i]}', dpi = 600)
        print(LGN_type[i])
        ax = fig.add_subplot(221)
        print(f'k: {LGN_k[0, j]}, {LGN_k[1, j]}')
        print(f'rw: {LGN_rw[0, j]}, {LGN_rw[1, j]}')
        ax.plot(sc[0,i,0,:], sc[1,i,0,:], 'ob', ms = 0.001)
        ax.plot(sc[0,i,1,:], sc[1,i,1,:], '>r', ms = 0.001)
        ax.set_aspect('equal')
        dwdhC = np.linalg.norm([sc[0,i,0,1] - sc[0,i,0,0], sc[1,i,0,1] - sc[1,i,0,0]]) * np.linalg.norm([sc[0,i,0,nSample1D] - sc[0,i,0,0], sc[1,i,0,nSample1D] - sc[1,i,0,0]])
        dwdhS = np.linalg.norm([sc[0,i,1,1] - sc[0,i,1,0], sc[1,i,1,1] - sc[1,i,1,0]]) * np.linalg.norm([sc[0,i,1,nSample1D] - sc[0,i,1,0], sc[1,i,1,nSample1D] - sc[1,i,1,0]])
        print(f'dwdh: {[dwdhC, dwdhS]}')
        ax.set_title(f'type {LGN_type[i]} SF = {SF[i]:.3f}')
        
        nSample1D = int(np.sqrt(nSample));
        ax = fig.add_subplot(222, projection = '3d')
        ax.plot3D(sc[0,i,0,:], sc[1,i,0,:], sw/dwdhC, '*', ms = 0.001)
        ax.plot3D(sc[0,i,1,:], sc[1,i,1,:], sw/dwdhS, '>', ms = 0.001)
        
        ax1 = fig.add_subplot(223)
        #ax2 = fig.add_subplot(224)
        #for j in np.random.randint(0,nLGN,(1000,)):
        #    ax1.plot(t, tw[j,0,:], 'r', lw = 0.1)
        #    ax2.plot(t, tw[j,1,:], 'b', lw = 0.1)
        ax1.plot(t, np.flipud(tw[i,0,:]*LGN_k[0,i]), 'm', lw = 1)
        ax1.plot(t, np.flipud(tw[i,1,:]*LGN_k[1,i]), 'g', lw = 1)
        ax1.plot(t, np.flipud(tw[i,0,:]*LGN_k[0,i] + tw[i,1,:]*LGN_k[1,i]), 'k', lw = 1)
        fig.savefig(fig_fdr+f'check_kernel_{j}-p{i}-{LGN_type[i]}' + suffix + '.png')
        print([np.sum(sw[:]), np.sum(tw[i,0,:]), np.sum(tw[i,1,:])])
    else:
        t = np.arange(mKernelSample)
        i = j - nParvo_I
        if i >= nMagno_I:
            i = i - nParvo_C
        assert(i>=0 and i<nMagno)
        fig = plt.figure(f'check_{j}-m{i}-{LGN_type[i]}', dpi = 600)
        print(LGN_type[i])
        ax = fig.add_subplot(221)
        print(f'k: {LGN_k[0, j]}, {LGN_k[1, j]}')
        print(f'rw: {LGN_rw[0, j]}, {LGN_rw[1, j]}')
        ax.plot(sc_m[0,i,:], sc_m[1,i,:], 'ob', ms = 0.001)
        ax.set_aspect('equal')
        dwdh = np.linalg.norm([sc_m[0,i,1] - sc_m[0,i,0], sc_m[1,i,1] - sc_m[1,i,0]]) * np.linalg.norm([sc_m[0,i,mSample1D] - sc_m[0,i,0], sc_m[1,i,mSample1D] - sc_m[1,i,0]])
        print(f'dwdh: {dwdh}')
        ax.set_title(f'SF = {SF[i]}')
        
        mSample1D = int(np.sqrt(mSample));
        ax = fig.add_subplot(222, projection = '3d')
        ax.plot3D(sc_m[0,i,:], sc_m[1,i,:], sw_m[i,:]/dwdh, '*', ms = 0.001)
        
        ax1 = fig.add_subplot(223)
        #ax2 = fig.add_subplot(224)
        #for j in np.random.randint(0,nLGN,(1000,)):
        #    ax1.plot(t, tw[j,0,:], 'r', lw = 0.1)
        #    ax2.plot(t, tw[j,1,:], 'b', lw = 0.1)
        ax1.plot(t, np.flipud(tw_m[i,:]), 'm', lw = 1)
        fig.savefig(fig_fdr+f'check_kernel_{j}-m{i}-{LGN_type[i]}' + suffix + '.png')
        print([np.sum(sw_m[i,:]), np.sum(tw_m[i,:])])

markers = ('^r', 'vg', '*g', 'dr', '^k', 'vb')
fig = plt.figure(f'check_multi-pattern', dpi = 150)
ax = fig.add_subplot(111, projection = '3d')
for i in iLGN:
    ax.plot3D(sc[0,i,0,:], sc[1,i,0,:], sw, markers[LGN_type[i]], ms = 0.1)
    #ax.plot(sc[0,i,1,:], sc[1,i,1,:], '>r', ms = 0.01)
    xs = ax.get_xlim()
    ys = ax.get_xlim()
    zs = ax.get_xlim()
    ax.set_box_aspect([np.ptp(xs),np.ptp(xs),np.ptp(zs)])
fig.savefig(fig_fdr+'check_multi-pattern' + suffix + '.png')


fig = plt.figure('hist', dpi = 600)
ax = fig.add_subplot(221)
ax.hist(max_convol[LGN_k[0,:]>0], bins=12, color = 'r', alpha = 0.5)
ax.hist(max_convol[LGN_k[0,:]<0], bins=12, color = 'b', alpha = 0.5)
print(f'max_convol:{[min(max_convol), np.mean(max_convol), max(max_convol)]}')
ax.set_title('max_convol')
ax = fig.add_subplot(222)
#ax.hist(nR, bin = 100,alpha = 0.5)
#ax.hist(delay, bin =100, alpha = 0.5)
_, bins, _ = ax.hist(LGN_k[0,:], bins = 20, color = 'r', alpha = 0.5)
print(f'on-centers: {np.sum(LGN_k[0,:] > 0)}, off-centers: {np.sum(LGN_k[0,:] < 0)}')
ax.hist(LGN_k[1,:], bins = bins, color = 'b', alpha = 0.5)
print(f'on-surround: {np.sum(LGN_k[1,:] > 0)}, off-surround: {np.sum(LGN_k[1,:] < 0)}')
ax.set_title('amp')
if nParvo > 0:
    ax = fig.add_subplot(223)
    ratio = np.abs(LGN_k[0,:]/(LGN_k[1,:]*np.max(tw[:,1,:])/np.max(tw[:,0,:])))
    max_k = np.max(abs(LGN_k[0,:]))
    for i in range(10):
        pick = np.logical_and(abs(LGN_k[0,:]) > i/10*max_k, abs(LGN_k[0,:]) < (i+1)/10*max_k)
        ax.plot(max_convol[pick], ratio[pick] , 'o', ms = 0.5, alpha = 0.5)
    ax.set_xlabel('max_convol')
    ax.set_ylabel('amp ratio')

ax = fig.add_subplot(224)
ax.plot(LGN_k[0,:], LGN_k[1,:] , 'o', ms = 1, alpha = 0.5)
ax.set_xlabel('center')
ax.set_ylabel('surround')

fig.savefig(fig_fdr+'spat_amplitude' + suffix + '.png')
