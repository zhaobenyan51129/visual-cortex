from patch_geo_func import x_ep, y_ep, model_block_ep
from repel_system import *
import matplotlib.pyplot as plt
import matplotlib.cm as cm 
from sys import stdout
from scipy import integrate
import numpy as np
import time
import py_compile
py_compile.compile('assign_attr.py')

class macroMap:
    def __init__(self, nx, ny, x, y, nblock, blockSize, LR_Pi_file, pos_file, OP_file, a, b, k, ecc, p0, p1, posUniform = False, OD_file = None, VF_file = None):
        self.nblock = nblock
        self.blockSize = blockSize
        self.networkSize = nblock * blockSize
        self.x = x
        self.y = y
        self.a = a
        self.b = b
        self.k = k
        self.nx = nx
        self.ny = ny
        self.xx, self.yy = np.meshgrid(x,y)
        with open(pos_file,'r') as f:
            pos = np.reshape(np.fromfile(f,'f8',count = 3*self.networkSize),(nblock,3,blockSize))
        self.pos = np.zeros((2,self.networkSize))
        self.pos[0,:] = pos[:,0,:].reshape(self.networkSize)
        self.pos[1,:] = pos[:,1,:].reshape(self.networkSize)
        self.zpos = pos[:,2,:]
        with open(LR_Pi_file,'r') as f:
            self.Pi = np.reshape(np.fromfile(f, 'i4', count = nx*ny),(ny,nx))
            self.LR = np.reshape(np.fromfile(f, 'i4', count = nx*ny),(ny,nx))
        self.LR[self.LR > 0] = 1
        self.LR[self.LR < 0] = -1
        self.LR[self.Pi <=0] = 0
        ratio = self.Pi.size/(np.sum(self.Pi>0))
        self.necc = np.round(nx * ratio).astype(int)
        self.npolar = np.round(ny * ratio).astype(int)
        self.ecc = ecc
        self.e_range = np.exp(np.linspace(np.log(1),np.log(ecc+1),self.necc))-1
        self.p_range = np.linspace(p0,p1,self.npolar)

        self.model_block = lambda p, e: model_block_ep(e,p,self.k,self.a,self.b)
        self.area = integrate.dblquad(self.model_block,0,self.ecc,self.p_range[0],self.p_range[-1])[0]
        self.subgrid = np.array([self.x[1] - self.x[0], self.y[1] - self.y[0]])
        memoryRequirement = ((np.int64(self.necc-1)*np.int64(self.npolar-1)*8 + np.int64(self.networkSize*(nx + ny)))*8/1024/1024/1024)
        print(f'{self.necc}x{self.npolar}, ecc-polar grid houses {self.networkSize} neurons')
        print(f'require {memoryRequirement:.3f} GB')
        self.vx = np.empty((self.necc,self.npolar))
        self.vy = np.empty((self.necc,self.npolar))
        for ip in range(self.npolar):
            self.vx[:,ip] = [x_ep(e,self.p_range[ip],self.k,self.a,self.b) for e in self.e_range]
            self.vy[:,ip] = [y_ep(e,self.p_range[ip],self.k,self.a,self.b) for e in self.e_range]
        
        # read preset orientation preferences
        if OP_file is not None:
            with open(OP_file,'r') as f:
                self.OPgrid = np.reshape(np.fromfile(f, 'f8', count = nx*ny),(ny,nx))
                assert(np.max(self.OPgrid[self.Pi>0]) <= np.pi/2 and np.min(self.OPgrid[self.Pi>0]) >= -np.pi/2)

        if VF_file is not None:
            with open(VF_file,'r') as f:
                self.vpos = np.reshape(np.fromfile(f, 'f8', count = self.networkSize*2),self.pos.shape)

        if OD_file is not None:
            with open(OD_file,'r') as f:
                self.ODlabel = np.fromfile(f, 'i4', count = self.networkSize)
        
        self.layer = None
        self.pODready = OD_file is not None
        self.pOPready = False
        self.LR_boundary_defined = False 
        self.pVFready = VF_file is not None 
        self.vposLready = VF_file is not None
        self.vposRready = VF_file is not None
        self.posUniform = posUniform
        # not used
        self.OD_VF_reconciled = False 

    # interpolate orientation preference for each neuron in from the OP grid
    def assign_pos_OP(self):
        if not self.posUniform:
            print('positions are not yet adjusted')
            return None
        i, j, coord = self.get_ij_grid(get_d2 = False, get_coord = True)

        #self.op = np.empty((self.networkSize))
        opgrid = (np.stack((self.OPgrid[i,j], self.OPgrid[i+1,j], self.OPgrid[i,j+1], self.OPgrid[i+1,j+1]), axis = -1) + np.pi/2)/np.pi
        assert(opgrid.shape[0] == self.networkSize)
        assert(opgrid.shape[1] == 4)
        a = opgrid[:,0] + coord[0,:] * (opgrid[:,2] - opgrid[:,0])
        b = opgrid[:,1] + coord[0,:] * (opgrid[:,3] - opgrid[:,1])
        self.op = a + coord[1,:]*(b - a)
        assert(self.op.size == self.networkSize)
        self.pOPready = True

        return self.op

    # memory requirement high, faster 
    def assign_pos_OD1(self, check = True):
        i, j, d2 = self.get_ij_grid(get_d2 = True, get_coord = False)
        print(np.sum(np.abs(self.LR[i,j]) + np.abs(self.LR[i+1,j]) + np.abs(self.LR[i,j+1]) + np.abs(self.LR[i+1,j+1]) == 0))

        print('adjust neuron positions near the boundary')
        # pick neurons that is outside the discrete ragged boundary
        outsideRaggedBound = ((self.Pi[i,j] <= 0) + (self.Pi[i+1,j] <= 0) + (self.Pi[i,j+1] <= 0) + (self.Pi[i+1,j+1] <= 0)).astype(bool)
        d2[self.Pi[i,j]<=0,    0] = np.float('inf')
        d2[self.Pi[i+1,j]<=0,  1] = np.float('inf')
        d2[self.Pi[i,j+1]<=0,  2] = np.float('inf')
        d2[self.Pi[i+1,j+1]<=0,3] = np.float('inf')
        nbp = np.sum((d2 == np.tile(np.array([np.float('inf'), np.float('inf'), np.float('inf'), np.float('inf')]), (self.networkSize,1))).any(-1))
        print(f'#boundary points: {nbp} ')
        assert(np.sum((d2 == np.tile(np.array([np.float('inf'), np.float('inf'), np.float('inf'), np.float('inf')]), (self.networkSize,1))).all(-1)) == 0)
        ipick = np.argmin(d2,1)
        
        # retain neurons inside the discrete ragged boundary
        x = np.mod(ipick[outsideRaggedBound],2)
        y = ipick[outsideRaggedBound]//2
        bx = self.xx[i[outsideRaggedBound] + x , j[outsideRaggedBound] + y]
        by = self.yy[i[outsideRaggedBound] + x , j[outsideRaggedBound] + y]
        self.pos[0,outsideRaggedBound] = bx + (self.pos[0,outsideRaggedBound]-bx)/3
        self.pos[1,outsideRaggedBound] = by + (self.pos[1,outsideRaggedBound]-by)/3

        print('assign ocular dominance preference to neuron according to their position in the cortex')
        self.ODlabel = np.zeros((self.networkSize), dtype = int)
        self.ODlabel[ipick == 0] = self.LR[i,    j][ipick == 0]
        self.ODlabel[ipick == 1] = self.LR[i+1,  j][ipick == 1]
        self.ODlabel[ipick == 2] = self.LR[i,  j+1][ipick == 2]
        self.ODlabel[ipick == 3] = self.LR[i+1,j+1][ipick == 3]

        assert(np.sum(self.ODlabel > 0) + np.sum(self.ODlabel < 0) == self.networkSize)

        print('retract neurons from the OD-boundary to avoid extreme repelling force later')
        # move neuron away from LR boundary to avoid extreme repelling force.
        # collect neurons in heterogeneous LR grid 
        LRgridType = np.stack((self.LR[i, j], self.LR[i+1, j], self.LR[i, j+1], self.LR[i+1, j+1]), axis=-1)
        bpick = np.logical_and(np.sum(LRgridType, axis=-1) != -4, np.sum(LRgridType, axis=-1) != 4)
        # exclude cortex boundary grids
        bpick = np.logical_and(bpick, np.logical_not(outsideRaggedBound))
        npick = np.sum(bpick)

        x = np.mod(ipick[bpick],2)
        y = ipick[bpick]//2
        bx = self.xx[i[bpick] + x , j[bpick] + y]
        by = self.yy[i[bpick] + x , j[bpick] + y]
        self.pos[0,bpick] = bx + (self.pos[0,bpick] - bx)/2
        self.pos[1,bpick] = by + (self.pos[1,bpick] - by)/2
        
        # checks
        if check:
            i, j, d2 = self.get_ij_grid(get_d2 = True, get_coord = False)
            ipick = np.argmin(d2,1)
            assert((self.Pi[i,    j][ipick == 0] > 0).all())
            assert((self.Pi[i+1,  j][ipick == 1] > 0).all())
            assert((self.Pi[i,  j+1][ipick == 2] > 0).all())
            assert((self.Pi[i+1,j+1][ipick == 3] > 0).all())
            for i in np.arange(self.networkSize):
                assert(np.sum((self.pos[:,i] - self.pos[:,i+1:].T == 0).all(-1))==0)
        
        self.pODready = True
        return self.ODlabel
    # boundary define by 4 corners
    def define_bound(self, grid):
        print('defining the boundary midway through the grid')
        ngrid = (self.nx-1) * (self.ny-1)
        bpGrid = np.empty((ngrid,2,3))
        btypeGrid = np.empty(ngrid, dtype = int)
        bgrid = np.stack((grid[:-1,:-1], grid[:-1,1:], grid[1:,1:], grid[1:,:-1]), axis=2)
        assert(bgrid.shape[0] == self.ny-1 and bgrid.shape[1] == self.nx-1 and bgrid.shape[2] == 4)
        bgrid = bgrid.reshape((ngrid,4))
        xx0 = self.xx[:-1,:-1].reshape(ngrid)
        xx1 = self.xx[:-1,1:].reshape(ngrid)
        yy0 = self.yy[:-1,:-1].reshape(ngrid)
        yy1 = self.yy[1:,:-1].reshape(ngrid)

        # unimplemented boundaries: if assertation error, increase the resolution of the grid
        unb = np.array([1,0,1,0], dtype = bool)
        unpick = (bgrid - unb == 0).all(-1)
        nunpick = np.sum(unpick)
        assert(nunpick == 0)
        unb = np.array([0,1,0,1], dtype = bool)
        unpick = (bgrid - unb == 0).all(-1)
        nunpick = nunpick + np.sum(unpick)
        assert(nunpick == 0)
        ## pick boundary
        # horizontal
        hb = np.array([0,0,1,1], dtype = bool)
        hpick = (bgrid - hb == 0).all(-1)
        hb = np.array([1,1,0,0], dtype = bool)
        hpick = np.logical_or(hpick, (bgrid - hb == 0).all(-1))
        nhpick = np.sum(hpick)
        if nhpick > 0:
            bpGrid[hpick,0,0] = xx0[hpick]
            bpGrid[hpick,0,1] = (xx0[hpick] + xx1[hpick])/2
            bpGrid[hpick,0,2] = xx1[hpick]
            bpGrid[hpick,1,:] = (yy0[hpick] + yy1[hpick]).reshape(nhpick,1)/2
        # vertical
        vb = np.array([1,0,0,1], dtype = bool)
        vpick = (bgrid - vb == 0).all(-1)
        vb = np.array([0,1,1,0], dtype = bool)
        vpick = np.logical_or(vpick, (bgrid - vb == 0).all(-1))
        nvpick = np.sum(vpick)
        if nvpick > 0:
            bpGrid[vpick,1,0] = yy0[vpick]
            bpGrid[vpick,1,1] = (yy0[vpick] + yy1[vpick])/2
            bpGrid[vpick,1,2] = yy1[vpick]
            bpGrid[vpick,0,:] = (xx0[vpick] + xx1[vpick]).reshape(nvpick,1)/2
        assert(np.logical_and(vpick,hpick).any() == False)
        ### first horizontal 0:1 then vertical 1:2
        def pick_boundary_in_turn(bpattern, xx, yy):
            pick = (bgrid - bpattern == 0).all(-1)
            bpattern = np.logical_not(bpattern)
            pick = np.logical_or(pick, (bgrid - bpattern == 0).all(-1))
            npick = np.sum(pick)
            if npick:
                bpGrid[pick,1,:2] = (yy0[pick] + yy1[pick]).reshape(npick,1)/2
                bpGrid[pick,0,1:] = (xx0[pick] + xx1[pick]).reshape(npick,1)/2
                bpGrid[pick,1,2] = yy[pick]
                bpGrid[pick,0,0] = xx[pick]
            return pick, npick

        # upper left
        ulpick, nulpick = pick_boundary_in_turn(np.array([1,0,0,0], dtype=bool), xx0, yy0)
        btype2pick = ulpick
        assert(np.logical_and(ulpick,hpick).any() == False)
        assert(np.logical_and(ulpick,vpick).any() == False)
        # lower left
        llpick, nllpick = pick_boundary_in_turn(np.array([0,0,0,1], dtype=bool), xx0, yy1)
        btype2pick = np.logical_or(btype2pick,llpick)
        assert(np.logical_and(llpick,hpick).any() == False)
        assert(np.logical_and(llpick,vpick).any() == False)
        assert(np.logical_and(llpick,ulpick).any() == False)
        # upper right 
        urpick, nurpick = pick_boundary_in_turn(np.array([0,1,0,0], dtype = bool), xx1, yy0)
        btype2pick = np.logical_or(btype2pick,urpick)
        assert(np.logical_and(urpick,hpick).any() == False)
        assert(np.logical_and(urpick,vpick).any() == False)
        assert(np.logical_and(urpick,ulpick).any() == False)
        assert(np.logical_and(urpick,llpick).any() == False)
        # lower right 
        lrpick, nlrpick = pick_boundary_in_turn(np.array([0,0,1,0], dtype = bool), xx1, yy1)
        btype2pick = np.logical_or(btype2pick,lrpick)
        assert(np.logical_and(lrpick,hpick).any() == False)
        assert(np.logical_and(lrpick,vpick).any() == False)
        assert(np.logical_and(lrpick,ulpick).any() == False)
        assert(np.logical_and(lrpick,llpick).any() == False)
        assert(np.logical_and(lrpick,urpick).any() == False)

        ## assemble
        btypeGrid[hpick] = 0
        btypeGrid[vpick] = 1
        btypeGrid[btype2pick] = 2
        nbtype2pick = np.sum([nulpick, nllpick, nurpick, nlrpick])
        nbtype = nhpick + nvpick + nbtype2pick

        nout = np.sum((bgrid-np.array([0,0,0,0], dtype = bool) == 0).all(-1))
        nin = np.sum((bgrid-np.array([1,1,1,1], dtype = bool) == 0).all(-1))
        assert(nbtype == ngrid - np.sum([nin, nout, nunpick]))

        btype = np.empty(nbtype, dtype = int)
        btype[:nhpick] = 0
        btype[nhpick:(nhpick+nvpick)] = 1
        btype[(nhpick+nvpick):] = 2
        bp  = np.empty((nbtype,2,3))
        bp[:nhpick,:,:] = bpGrid[hpick,:,:] 
        bp[nhpick:(nhpick+nvpick),:,:] = bpGrid[vpick,:,:]
        bp[(nhpick+nvpick):,:,:] = bpGrid[btype2pick,:,:]
        return bp, btype
    #awaits vectorization
    def assign_pos_VF(self, straightFromPos = False):
        if not (hasattr(self, 'vpos') and self.vposLready and self.vposRready) and not straightFromPos:
            raise Exception('vpos is not ready')
        d0 = np.zeros(self.npolar-1)
        d1 = np.zeros(self.npolar-1)
        ix0 = np.zeros(self.npolar-1,dtype='int')
        if straightFromPos:
            vpos = self.pos.copy()
        else:
            vpos = self.vpos.copy()
        # top polar line excluded such that the coord of the nearest vertex will always be left and lower to the neuron's position, ready for interpolation
        for i in range(self.networkSize):
            pos = np.empty(2)
            pos[0] = vpos[0,i]
            pos[1] = vpos[1,i]
            # vx/vy(ecc,polar)
            mask = np.logical_and(pos[0] - self.vx[:-1,:-1] > 0, pos[0] - self.vx[1:,:-1] < 0)
            # find iso-polar lines whose xrange include x-coord of the neuron 
            pmask = mask.any(0)
            # find iso-polar lines whose xrange does not include x-coord of the neuron 
            pnull = np.logical_not(pmask)
            # find the preceding ecc index of the iso-polar lines that does includ the x-coord
            ix = np.nonzero(mask.T)[1]
            ix0[pmask] = ix
            ix0[pnull] = -1
            # calculate distance to the nearby VF grid vertex
            d0[pmask] = np.power(self.vx[ix,  np.arange(self.npolar-1)[pmask]] - pos[0],2) + np.power(self.vy[ix,  np.arange(self.npolar-1)[pmask]] - pos[1],2)
            d1[pmask] = np.power(self.vx[ix+1,np.arange(self.npolar-1)[pmask]] - pos[0],2) + np.power(self.vy[ix+1,np.arange(self.npolar-1)[pmask]] - pos[1],2)
            d0[pnull] = np.float('inf')
            d1[pnull] = np.float('inf')
            #find minimum distance to the nearest vertex
            dis = np.min(np.vstack([d0, d1]),0)
            # get the ecc and polar indices of the vertex
            idp = np.argmin(dis) # polar index
            idx = ix0[idp] # ecc index
            ## interpolate VF-ecc to pos
            vpos[0,i] = np.exp(np.log(self.e_range[idx]+1) + (np.log(self.e_range[idx+1]+1) - np.log(self.e_range[idx]+1)) * np.sqrt(dis[idp])/(np.sqrt(d0[idp])+np.sqrt(d1[idp])))-1
            ## interpolate VF-polar to pos
            vp_y0 = y_ep(vpos[0,i],self.p_range[idp],self.k,self.a,self.b)
            vp_x0 = x_ep(vpos[0,i],self.p_range[idp],self.k,self.a,self.b)
            vp_y1 = y_ep(vpos[0,i],self.p_range[idp+1],self.k,self.a,self.b)
            vp_x1 = x_ep(vpos[0,i],self.p_range[idp+1],self.k,self.a,self.b)
            dp0 = np.sqrt(np.power(pos[0]-vp_x0,2) + np.power(pos[1]-vp_y0,2))
            dp1 = np.sqrt(np.power(pos[0]-vp_x1,2) + np.power(pos[1]-vp_y1,2))
            vpos[1,i] = self.p_range[idp] + (self.p_range[idp+1] - self.p_range[idp]) * dp0/(dp0+dp1)
            #assert(vpos[1,i] >= self.p_range[0] and vpos[1,i] <= self.p_range[-1])
            stdout.write(f'\rassgining visual field: {(i+1)/self.networkSize*100:.3f}%')
        stdout.write('\n')
        self.pVFready = True
        return vpos

    def define_bound_LR(self):
        # right OD boundary 
        LR = self.LR.copy()
        LR[self.Pi < 1] = 0
        LR[self.LR == -1] = 0
        self.OD_boundR, self.btypeR = self.define_bound(LR)
        # left OD boundary 
        LR[self.LR == -1] = 1
        LR[self.LR == 1] = 0
        self.OD_boundL, self.btypeL = self.define_bound(LR)
        self.LR_boundary_defined = True

    def diffuse_bound(self, LR):
        print('diffuse the boudnary for spreading vpos')
        nLR = np.sum(LR > 0)
        tmpLR = LR[1:-1,1:-1]
        i, j = np.nonzero(tmpLR > 0)
        i = i + 1
        j = j + 1
        LR[i+1,j+1] = 1
        LR[i+1,j-1] = 1
        LR[i-1,j+1] = 1
        LR[i-1,j-1] = 1
        ngrid = (self.nx-1) * (self.ny-1)
        LRgrid = np.stack((LR[:-1,:-1], LR[:-1,1:], LR[1:,1:], LR[1:,:-1]), axis=2)
        LRgrid = LRgrid.reshape((ngrid,4))
        # pick touching boundaries
        pick = (LRgrid - np.array([1,0,1,0]) == 0).all(-1)
        pick = np.logical_or(pick, (LRgrid - np.array([0,1,0,1]) == 0).all(-1))
        indices = np.nonzero(pick)[0]
        p, q = np.unravel_index(indices, (self.ny-1, self.nx-1))
        # asserts non-functional
        pick = LR[p, q] == 1
        assert((LR[p[pick], q[pick] + 1] == 0).all())
        assert((LR[p[pick] + 1, q[pick] + 1] == 1).all())
        assert((LR[p[pick] + 1, q[pick]] == 0).all())
        pick = LR[p, q] == 0
        assert((LR[p[pick], q[pick] + 1] == 1).all())
        assert((LR[p[pick] + 1, q[pick] + 1] == 0).all())
        assert((LR[p[pick] + 1, q[pick]] == 1).all())
        # merge
        LR[p  ,   q] = 1
        LR[p  , q+1] = 1 
        LR[p+1, q+1] = 1 
        LR[p+1,   q] = 1 
        # do not expand outside of cortex
        LR[self.Pi<=0] = 0
        spreaded = False 
        if np.sum(LR > 0) == np.sum(self.Pi > 0):
            spreaded = True
            print('spread finished')
        else:
            assert(nLR < np.sum(LR > 0))
        return LR, spreaded
         
    def check_pos(self):
        # check in boundary
        i, j, d2 = self.get_ij_grid(get_d2 = True, get_coord = False)
        ipick = np.argmin(d2,1)
        # in the shell
        assert((self.Pi[i,    j][ipick == 0] > 0).all())
        assert((self.Pi[i+1,  j][ipick == 1] > 0).all())
        assert((self.Pi[i,  j+1][ipick == 2] > 0).all())
        assert((self.Pi[i+1,j+1][ipick == 3] > 0).all())
        # in the R stripe
        pR = self.ODlabel > 0
        assert((self.LR[i,    j][np.logical_and(ipick == 0, pR)] == 1).all())
        assert((self.LR[i+1,  j][np.logical_and(ipick == 1, pR)] == 1).all())
        assert((self.LR[i,  j+1][np.logical_and(ipick == 2, pR)] == 1).all())
        assert((self.LR[i+1,j+1][np.logical_and(ipick == 3, pR)] == 1).all())
        # in the L stripe
        pL = self.ODlabel < 0
        assert((self.LR[i,    j][np.logical_and(ipick == 0, pL)] == -1).all())
        assert((self.LR[i+1,  j][np.logical_and(ipick == 1, pL)] == -1).all())
        assert((self.LR[i,  j+1][np.logical_and(ipick == 2, pL)] == -1).all())
        assert((self.LR[i+1,j+1][np.logical_and(ipick == 3, pL)] == -1).all())
        print('boundary and LR checked')

    def make_pos_uniformT(self, dt, seed = None, particle_param = None, boundary_param = None, ax1 = None, ax2 = None, check = True, fixed = None):
        subarea = self.subgrid[0] * self.subgrid[1]
        area = subarea * np.sum(self.Pi > 0)
        print(f'grid area: {area}, used in simulation')
        A = self.Pi.copy()
        A[self.Pi <= 0] = 0
        A[self.Pi > 0] = 1
        OD_bound, btype = self.define_bound(A)

        oldpos = self.pos.copy()
        self.pos, convergence, nlimited, _ = simulate_repel(area, self.subgrid, self.pos, dt, OD_bound, btype, boundary_param, particle_param, ax = ax1, seed = seed, fixed = fixed)
        if check:
            self.check_pos()

    def make_pos_uniform(self, dt, seed = None, particle_param = None, boundary_param = None, ax1 = None, ax2 = None, check = True):
        if not self.pODready:
            self.assign_pos_OD1()
        pR = self.ODlabel > 0
        pL = self.ODlabel < 0
        nR = np.sum(pR)
        nL = np.sum(pL)
        areaL = self.area * nL/(nR+nL)
        areaR = self.area * nR/(nR+nL)
        print(f'smooth area: {areaL}, {areaR}')
        subarea = self.subgrid[0] * self.subgrid[1]
        areaR = subarea * np.sum(self.LR == 1)
        areaL = subarea * np.sum(self.LR == -1)
        print(f'grid area: {areaL}, {areaR}, used in simulation')
        if self.LR_boundary_defined is False:
            self.define_bound_LR()

        oldpos = self.pos.copy()
        self.pos[:,pL], convergenceL, nlimitedL, _ = simulate_repel(areaL, self.subgrid, self.pos[:,pL], dt, self.OD_boundL, self.btypeL, boundary_param, particle_param, ax = ax1, seed = seed)
        if check:
            self.check_pos()
        self.pos[:,pR], convergenceR, nlimitedR, _ = simulate_repel(areaR, self.subgrid, self.pos[:,pR], dt, self.OD_boundR, self.btypeR, boundary_param, particle_param, ax = ax2, seed = seed)
        if check:
            self.check_pos()

        if not self.posUniform:
            self.posUniform = True
        return oldpos, convergenceL, convergenceR, nlimitedL, nlimitedR

    def spread_pos_VF(self, dt, vpfile, lrfile, LRlabel, seed = None, firstTime = True, particle_param = None, boundary_param = None, ax = None, p_scale = 2.0, b_scale = 1.0):
        ngrid = np.sum(self.Pi).astype(int)
        if LRlabel == 'L':
            LRpick = self.ODlabel < 0
        else:
            assert(LRlabel == 'R')
            LRpick = self.ODlabel > 0

        if not hasattr(self, 'vpos'):
            # dont reinit for the other stripe
            self.vpos = self.pos.copy() # always init with pos
        if firstTime is True:
            LR = self.LR.copy()
            if LRlabel == 'L':
                LR[LR > 0] = 0
                LR[LR < 0] = 1
            else:
                LR[LR < 0] = 0
                LR[LR > 0] = 1
        else:
            with open(vpfile,'rb') as f:
                self.vpos[:,LRpick] = np.fromfile(f).reshape(2, np.sum(LRpick))
            with open(lrfile,'rb') as f:
                LR = np.fromfile(f).reshape(self.Pi.shape)

        if ax is not None:
            if seed is None:
                seed = np.int64(time.time())
            np.random.seed(seed)
            nLR = np.sum(LRpick)
            nsLR = np.int(nLR*0.1)
            print(f'sample size: {nsLR}')
            pick = np.random.choice(nLR, nsLR, replace = False)
            #pick = np.arange(nLR)

        final = True 
        if not final:
            spreaded = False # at least one time
            ip = 0
            ppos = None
            starting = True
            while spreaded is False:
                self.vpos[:, LRpick], LR, spreaded, ppos, ip, OD_bound = self.spread(dt, self.vpos[:, LRpick], LR, particle_param, boundary_param, ax, pick, ppos, ip, starting, p_scale = p_scale, b_scale = b_scale)
                starting = False
                print(f'{np.sum(LR).astype(int)}/{ngrid}')
                with open(vpfile,'wb') as f:
                    self.vpos[:, LRpick].tofile(f)
                with open(lrfile,'wb') as f:
                    LR.tofile(f)
        else:
            self.vpos[:, LRpick], _, _, OD_bound = self.spread(dt, self.vpos[:, LRpick], LR, particle_param, boundary_param, ax = None, pick = None, p_scale = p_scale, b_scale = b_scale)
            with open(vpfile,'wb') as f:
                self.vpos[:, LRpick].tofile(f)
            with open(lrfile,'wb') as f:
                LR.tofile(f)
        if ax is not None:
            # connecting points on grid sides
            ax.plot(OD_bound[:,0,[0,2]].squeeze(), OD_bound[:,1,[0,2]].squeeze(), ',r')
            # grid centers
            ax.plot(OD_bound[:,0,1].squeeze(), OD_bound[:,1,1].squeeze(), ',g')
            if final:
                # plot all displacement
                ax.plot(np.vstack((self.pos[0,LRpick], self.vpos[0,LRpick])), np.vstack((self.pos[1,LRpick], self.vpos[1,LRpick])),'-,c', lw =0.01)
            # final positions
            ax.plot(self.vpos[0,LRpick], self.vpos[1,LRpick], ',k')
        # check in boundary
        i, j, d2 = self.get_ij_grid(get_d2 = True, get_coord = False)
        ipick = np.argmin(d2,1)
        # in the LR stripe
        assert((LR[i,    j][np.logical_and(ipick == 0, LRpick)] == 1).all())
        assert((LR[i+1,  j][np.logical_and(ipick == 1, LRpick)] == 1).all())
        assert((LR[i,  j+1][np.logical_and(ipick == 2, LRpick)] == 1).all())
        assert((LR[i+1,j+1][np.logical_and(ipick == 3, LRpick)] == 1).all())

        if LRlabel == 'L':
            self.vposLready = True
        else:
            self.vposRready = True

    def spread(self, dt, pos, LR, particle_param = None, boundary_param = None, ax = None, pick = None, ppos = None, ip = 0, starting = True, p_scale = 2.0, b_scale = 1.0):
        if starting and ax is not None:
            OD_bound, btype = self.define_bound(LR)
            # connecting points on grid sides
            ax.plot(OD_bound[:,0,[0,2]].squeeze(), OD_bound[:,1,[0,2]].squeeze(), ',r')
            # grid centers
            ax.plot(OD_bound[:,0,1].squeeze(), OD_bound[:,1,1].squeeze(), ',g')
        subarea = self.subgrid[0] * self.subgrid[1]

        old_area = subarea * np.sum(LR == 1)
        n = pos.shape[1]
        LR, spreaded = self.diffuse_bound(LR)
        area = subarea * np.sum(LR == 1)
        print(f'area increases {area/old_area}%')
        
        OD_bound, btype = self.define_bound(LR)

        if ax is not None:
            assert(pick is not None)
            if ppos is None:
                ppos = np.empty((2,2,pick.size)) # start/ending, x/y, selected id
                ppos[0,:,:] = pos[:,pick].copy()

        pos, _, _, _ = simulate_repel(area, self.subgrid, pos, dt, OD_bound, btype, boundary_param, particle_param, p_scale = p_scale, b_scale = b_scale)
        if ax is not None:
            ip = ip + 1
            ppos[ip%2,:,:] = pos[:,pick].copy()
            ax.plot(ppos[:,0,:].squeeze(), ppos[:,1,:].squeeze(), '-,c', lw = 0.01)

            return pos, LR, spreaded, ppos, ip, OD_bound
        else:
            return pos, LR, spreaded, OD_bound

    def get_ij_grid(self, get_d2 = True, get_coord = True):
        print('get the index of the nearest vertex for each neuron in its own grid')

        x0 = self.x[:-1]
        x1 = self.x[1:]
        y0 = self.y[:-1]
        y1 = self.y[1:]

        i = np.nonzero(np.logical_and(np.tile(self.pos[1,:],(self.ny-1,1))-y0.reshape(self.ny-1,1) > 0, np.tile(self.pos[1,:],(self.ny-1,1))-y1.reshape(self.ny-1,1) < 0).T)[1]
        assert(i.size == self.networkSize)
        j = np.nonzero(np.logical_and(np.tile(self.pos[0,:],(self.nx-1,1))-x0.reshape(self.nx-1,1) > 0, np.tile(self.pos[0,:],(self.nx-1,1))-x1.reshape(self.nx-1,1) < 0).T)[1]
        assert(j.size == self.networkSize)
        if not get_d2 and not get_coord:
            return i, j
        else:
            if get_d2:
                corner_x = np.zeros((self.ny-1,self.nx-1,4))
                corner_x[:,:,0] = self.xx[:-1,:-1]
                corner_x[:,:,1] = self.xx[1:,:-1]
                corner_x[:,:,2] = self.xx[:-1,1:]
                corner_x[:,:,3] = self.xx[1:,1:]
                corner_y = np.zeros((self.ny-1,self.nx-1,4))
                corner_y[:,:,0] = self.yy[:-1,:-1]
                corner_y[:,:,1] = self.yy[1:,:-1]
                corner_y[:,:,2] = self.yy[:-1,1:]
                corner_y[:,:,3] = self.yy[1:,1:]
                print('calculate neurons\' cortical distance to the nearest vertex in the grid')
                d2 = np.zeros((4,self.networkSize))
                for ic in range(4):
                    dx = self.pos[0,:] - corner_x[i,j,ic]
                    dy = self.pos[1,:] - corner_y[i,j,ic]
                    d2[ic,:] = np.power(dx,2) + np.power(dy,2)

            if get_coord:
                corner_x = np.zeros((self.ny-1,self.nx-1,2))
                corner_x[:,:,0] = self.xx[:-1,:-1]
                corner_x[:,:,1] = self.xx[:-1,1:]
                corner_y = np.zeros((self.ny-1,self.nx-1,2))
                corner_y[:,:,0] = self.yy[:-1,:-1]
                corner_y[:,:,1] = self.yy[1:,:-1]
                coord = np.empty((2,self.networkSize))
                print('calculate neurons\' normalized coordinate in its grid')
                coord[0,:] = (self.pos[0,:] - corner_x[i,j,0])/(corner_x[i,j,1] - corner_x[i,j,0])
                coord[1,:] = (self.pos[1,:] - corner_y[i,j,0])/(corner_y[i,j,1] - corner_y[i,j,0])

            if get_coord and get_d2:
                return i, j, d2.T, coord
            elif get_coord:
                return i, j, coord
            else:
                return i, j, d2.T

    def plot_map(self,ax1,ax2,ax3,dpi,pltOD=True,pltVF=True,pltOP=True,ngridLine=4):
        if pltOD:
            #if not self.pODready:
                #self.assign_pos_OD0()
                #self.assign_pos_OD1()
                
            if pltOP:
                if not self.pOPready:
                    if self.assign_pos_OP() is None:
                        raise Exception('Orientation Preference is not plotted')
                bMS = 1 * np.power(72,2)/self.networkSize
                sMS = 4 * np.power(1/dpi,2)
                #s = max(bMS, sMS)
                s = sMS
                hsv = cm.get_cmap('hsv')
                print('matplotlib \'plot\' is inefficient so will take a long time (\'scatter\' is buggy)')
                pick = self.ODlabel>0 
                for i in np.arange(sum(pick)):
                    ax1.plot(self.pos[0,pick][i], self.pos[1,pick][i], markersize = 1/dpi, marker = ',', c = hsv(self.op[pick][i]))
                print('50% done')
                pick = self.ODlabel<0 
                for i in np.arange(sum(pick)):
                    ax1.plot(self.pos[0,pick][i], self.pos[1,pick][i], markersize = 1/dpi, marker = ',', c = hsv(self.op[pick][i])*0.75)
            else:
                ax1.plot(self.pos[0,:], self.pos[1,:],',k')
                ax1.plot(self.xx[self.Pi<=0], self.yy[self.Pi<=0],',r')
                ax1.plot(self.xx[self.Pi>0], self.yy[self.Pi>0],',g')
                #ax1.plot(self.pos[0,self.ODlabel>0], self.pos[1,self.ODlabel>0],',m')
                #ax1.plot(self.pos[0,self.ODlabel<0], self.pos[1,self.ODlabel<0],',c')

            if ngridLine > 0:
                for ip in range(self.npolar):
                    if ip % (self.npolar//ngridLine)== 0:
                        ax1.plot(self.vx[:,ip], self.vy[:,ip],':',c='0.5', lw = 0.1)
                for ie in range(self.necc):
                    if ie % (self.necc//ngridLine)== 0:
                        ax1.plot(self.vx[ie,:], self.vy[ie,:],':',c='0.5', lw = 0.1)

        if pltVF == True:
            if self.pVFready == False:
                raise Exception('get VF ready first: 1) make_pos_uniform for L and R. 2) spread_pos_VF for L and R. 3) assign_pos_VF')
            plt.sca(ax2)
            plt.polar(self.vpos[1,self.ODlabel>0], self.vpos[0,self.ODlabel>0],',m')
            if ngridLine > 0:
                for ip in range(self.npolar):
                    if ip % (self.npolar//ngridLine)== 0:
                        plt.polar(self.p_range[ip]+np.zeros(self.necc), self.e_range,':',c='0.5', lw = 0.1)
                for ie in range(self.necc):
                    if ie % (self.necc//ngridLine)== 0:
                        plt.polar(self.p_range, self.e_range[ie]+np.zeros(self.npolar),':',c='0.5', lw = 0.1)

            plt.sca(ax3)
            plt.polar(self.vpos[1,self.ODlabel<0], self.vpos[0,self.ODlabel<0],',m')
            if ngridLine > 0:
                for ip in range(self.npolar):
                    if ip % (self.npolar//ngridLine)== 0:
                        plt.polar(self.p_range[ip]+np.zeros(self.necc), self.e_range,':',c='0.5', lw = 0.1)
                for ie in range(self.necc):
                    if ie % (self.necc//ngridLine)== 0:
                        plt.polar(self.p_range, self.e_range[ie]+np.zeros(self.npolar),':',c='0.5', lw = 0.1)


    def save(self, pos_file = None, OD_file = None, VF_file = None):
        if pos_file is not None:
            with open(pos_file,'wb') as f:
                pos = np.empty((self.nblock, 3, self.blockSize))
                pos[:,0,:] = self.pos[0,:].reshape(self.nblock,self.blockSize)
                pos[:,1,:] = self.pos[1,:].reshape(self.nblock,self.blockSize)
                pos[:,2,:] = self.zpos
                pos.tofile(f)
        if OD_file is not None:
            with open(OD_file,'wb') as f:
                self.ODlabel.tofile(f)
        if VF_file is not None:
            with open(VF_file,'wb') as f:
                self.vpos.tofile(f)

    ######## rarely-used functions ##############
    # memory requirement low, slower
    def assign_pos_OD0(self):
        ## determine which blocks to be consider in each subgrid to avoid too much iteration over the whole network
        # calculate reach of each block as its radius, some detached blocks may be included
        pos = self.pos.reshape(2,self.nblock,self.blockSize)
        blockPosX = np.reshape(np.mean(pos[0,:,:],1), (self.nblock,1))
        blockPosY = np.reshape(np.mean(pos[1,:,:],1), (self.nblock,1))
        max_dis2center = np.max(np.power(pos[0,:,:]-blockPosX,2) + np.power(pos[1,:,:]-blockPosY,2),1).reshape((self.nblock,1))
        # iterate over each grid
        corner = np.zeros((2,4))
        self.ODlabel = np.zeros((self.networkSize), dtype=int)
        for i in range(self.ny-1):
            for j in range(self.nx-1):
                nc = np.sum(self.Pi[i:i+2,j:j+2])
                ic = (self.Pi[i:i+2,j:j+2]>0).reshape(4)
                if nc > 0:
                    corner[:,0] = [self.x[j],   self.y[i]]
                    corner[:,1] = [self.x[j+1], self.y[i]]
                    corner[:,2] = [self.x[j],   self.y[i+1]]
                    corner[:,3] = [self.x[j+1], self.y[i+1]]
                    # see if any corner is closer to each block than its radius
                    dx = np.tile(corner[0,:],(self.nblock,1)) - blockPosX
                    dy = np.tile(corner[1,:],(self.nblock,1)) - blockPosY
                    d2 = np.power(dx,2) + np.power(dy,2)
                    blist = np.nonzero((d2 < max_dis2center).any(1))[0]
                    nb = blist.size
                    OD_of_grid = self.LR[i:i+2,j:j+2]
                    gridLR = np.sum(OD_of_grid[self.Pi[i:i+2,j:j+2]])
                    for ib in blist:
                        #pick neurons that are inside the subgrid
                        ipick = np.logical_and(pos[0,ib,:] > self.x[j], pos[0,ib,:] < self.x[j+1])
                        ipick = np.logical_and(ipick, np.logical_and(pos[1,ib,:] > self.y[i], pos[1,ib,:] < self.y[i+1]))
                        bpick = np.arange(ib*self.blockSize,(ib+1)*self.blockSize)[ipick]
                        npick = np.sum(ipick)
                        if npick > 0:
                            if gridLR == nc:
                                self.ODlabel[bpick] = 1
                            else:
                                if gridLR == -nc:
                                    self.ODlabel[bpick] = -1
                                else:
                                    dx = np.tile(pos[0,ib,ipick],(nc,1)) - corner[0,ic].reshape(nc,1)
                                    dy = np.tile(pos[1,ib,ipick],(nc,1)) - corner[1,ic].reshape(nc,1)
                                    d2 = np.power(dx,2) + np.power(dy,2)
                                    OD_flattened = OD_of_grid.reshape(4)[ic]
                                    OD_of_neuron = np.argmin(d2,0)
                                    self.ODlabel[bpick] = OD_flattened[OD_of_neuron]
                stdout.write(f'\r{(i*(self.nx-1)+j+1)/(self.nx-1)/(self.ny-1)*100:.3f}%, grid ({i+1},{j+1})/({self.ny-1},{self.nx-1})')
        stdout.write('\n')
        self.pODready = True
        return self.ODlabel

    def flip_pos_along_OD(self, seed=None):
        if self.OD_VF_reconciled == False:
            if self.pVFready == False:
                self.assign_pos_VF()
            if self.pODready == False:
                self.assign_pos_OD1()
            label = np.copy(self.ODlabel)

            np.random.seed(seed)
            np.random.shuffle(label)
            R0 = self.ODlabel>0
            L0 = self.ODlabel<0
            R1 = label>0
            L1 = label<0

            # positional Right shuffled to Left OD to sample visual field
            pR = np.logical_and(R0,L1)
            # positional Left shuffled to Right OD to sample visual field
            pL = np.logical_and(L0,R1)

            assert(np.logical_and(pR,pL).any()==False)
            nR = np.sum(pR)
            nL = np.sum(pL) 
            assert(nR == nL)
            print(f'shuffled {nR} pairs, requiring {nL*nR*8/1024/1024/1024:.3f} Gb')
            # calculate distance
            Rind = np.arange(self.networkSize)[pR]
            Lind = np.arange(self.networkSize)[pL]
            disMat = np.power(np.tile(self.pos[0,pR],(nL,1)) - self.pos[0,pL].reshape(nL,1),2) + np.power(np.tile(self.pos[1,pR],(nL,1)) - self.pos[1,pL].reshape(nL,1),2)
            # bring back visual field position
            ind = np.argsort(disMat,1)
            print('distance of shuffled pairs sorted')
            l_range = np.arange(nL)
            rsel = np.ones(nR,dtype=bool)
            lsel = np.ones(nR,dtype=bool)
            iq = np.zeros(nR,dtype=int)
            for i in range(nR):
                # pick next min from all rows
                head = disMat[l_range[lsel],ind[l_range[lsel],iq[lsel]]]
                # pos id for min of all pairs
                assert(head.size == np.sum(lsel))
                indL = l_range[lsel][np.argmin(head)]
                indR = ind[indL,iq[indL]]
                # update bool select vector
                assert(lsel[indL] == True)
                assert(rsel[indR] == True)
                assert(Rind[indR] != Lind[indL])
                lsel[indL] = False
                rsel[indR] = False
                for j in l_range[lsel]: 
                    while rsel[ind[j,iq[j]]] == False:
                        iq[j] = iq[j] + 1
                ### NOTE: deep copy is required when swap vector
                self.vpos[:,Lind[indL]], self.vpos[:,Rind[indR]] = self.vpos[:,Rind[indR]].copy(), self.vpos[:,Lind[indL]].copy()
                stdout.write(f'\rreconciling OD and VF: {(i+1)/nR*100:.3f}%')
            stdout.write('\n')
            self.OD_VF_reconciled = True

            return self.vpos
