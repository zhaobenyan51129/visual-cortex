import numpy as np
from scipy.stats import qmc

def square_pos(per_dis, w, h, center):
    sampler = qmc.Sobol(d=2)
    rands = sampler.random(w*h)
    pos = np.zeros((2,w*h))
    pos[0,:] = (w*rands[:,0]-w/2)*per_dis[0] + center[0]
    pos[1,:] = (h*rands[:,1]-h/2)*per_dis[1] + center[1]
    return pos

def square_OP(center, r, phase, pos):
    dis = pos - center
    op = np.arctan2(dis) + phase
    pick = (pos-center).all(1) < r
    return op, pick
