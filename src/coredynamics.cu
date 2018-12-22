#include "coredynamics.h"

__global__ void recal_G(double* __restrict__ g,
                        double* __restrict__ h,
                        double* __restrict__ preMat,
                        double* __restrict__ gactVec,
                        double* __restrict__ hactVec,
                        double* __restrict__ g_b1x,
                        double* __restrict__ h_b1x,
                        unsigned int n, unsigned int offset, unsigned int ngType, unsigned int ns, int m) 
{
    // 2D blockGrid
    // -> D-1 pieces of actVec 
    // -> D-2 pieces of post-synaptic neurons 
    // 1D threadBlock
    extern __shared__ double actVec[];
    double *gaV = actVec;
    double *haV = &(actVec[ngType*ns]);
    unsigned int id = blockDim.x*blockIdx.y + threadIdx.x;
    unsigned int ss = ns/m;
    #pragma unroll
    for (int ig=0; ig<ngType; ig++) {
        #pragma unroll
        for (int i=0; i<m; i++) {
            // av = double[ngType,#(ns),ns]
            // actVec = double[ngType,n]
            if (threadIdx.x < ss) {
                unsigned int sid = ig*ns + (i*ss + threadIdx.x);
                unsigned int gid = (ig*n + offset + ns*blockIdx.x) + (i*ss + threadIdx.x);
                gaV[sid] = gactVec[gid];
                haV[sid] = hactVec[gid];
            }
        }
    }
    __syncthreads();
    for (int ig=0; ig<ngType; ig++) {
        double g_t = 0.0f;
        double h_t = 0.0f;
        for (int i = 0; i<ns; i++) {
            unsigned sid = ig*ns + i;
            if (gaV[sid] > 0) {
                unsigned pid = (offset + blockIdx.x*ns + i)*n + id;
                double s = preMat[pid];
                g_t += gaV[sid] * s;
                h_t += haV[sid] * s;
            }
        }
        if (gridDim.x < 32) {
            if (g_t > 0) {
                unsigned int gid = ig*n + id;
                atomicAdd(&(g[gid]), g_t);
                atomicAdd(&(h[gid]), h_t);
            }
        } else {
            // b1x = double[ngType, n/ns(gridDim.x), n]
            unsigned int b1xid = ig*n*gridDim.x + blockIdx.x*n + id;
            g_b1x[b1xid] = g_t;
            h_b1x[b1xid] = h_t;
        }
    }
}

__global__ void reduce_G(double* __restrict__ g,
                         double* __restrict__ h,
                         double* __restrict__ g_b1x, 
                         double* __restrict__ h_b1x,
                         unsigned int ngType, int n) 
{ 
    // b1x = double[ngType, n/ns(gridDim.x), n]
    // n x #(ns)
    extern __shared__ double blk[];
    double* g_blk = blk;
    double* h_blk = &(blk[blockDim.x]);
    for (int ig=0; ig<ngType; ig++) {
        unsigned int gid = ig*blockDim.x*gridDim.x + threadIdx.x*gridDim.x + blockIdx.x;
        if (gid < n) {
            // can do coalesce read optimization here (transpose in shared mem)
            g_blk[threadIdx.x] = g_b1x[gid];
            h_blk[threadIdx.x] = g_b1x[gid];
        } else {
            g_blk[threadIdx.x] = 0.0f;
            h_blk[threadIdx.x] = 0.0f;
        }
        __syncthreads();
        for (int i=blockDim.x/2; i>=32; i>>=1) {
            if (threadIdx.x < i) {
                g_blk[threadIdx.x] += g_blk[threadIdx.x + i];
                h_blk[threadIdx.x] += h_blk[threadIdx.x + i];
            }
            __syncthreads();
        }
        if (threadIdx.x < 32) {
            double g_warp = g_blk[threadIdx.x];
            double h_warp = h_blk[threadIdx.x];
            for (int offset = 16; offset > 0; offset /= 2) {
                g_warp += __shfl_down_sync(FULL_MASK, g_warp, offset);  
                h_warp += __shfl_down_sync(FULL_MASK, h_warp, offset);  
            }
            if (threadIdx.x == 0) {
                unsigned int id = ig*gridDim.x + blockIdx.x;
                g[id] += g_warp;
                h[id] += g_warp;
            }
        }
    }
}

__global__ void logRand_init(double *logRand, curandStateMRG32k3a *state, unsigned long long seed) {
    unsigned int id = blockIdx.x * blockDim.x + threadIdx.x;
    curandStateMRG32k3a localState = state[id];
    curand_init(seed+id, 0, 0, &localState);
    logRand[id] = -log(curand_uniform_double(&localState));
    //printf("logRand0 = %f\n", logRand[id]);
    //logRand[id] = 1.0f;
    state[id] = localState;
}

__global__ void randInit(double* __restrict__ preMat, 
						 double* __restrict__ v, 
						 double* __restrict__ lTR, 
						 curandStateMRG32k3a* __restrict__ state,
double s, unsigned int networkSize, unsigned long long seed, double dInput) {
    unsigned int id = blockIdx.x * blockDim.x + threadIdx.x;
    curandStateMRG32k3a localState = state[id];
    curand_init(seed+id, 0, 0, &localState);
    v[id] = vL + curand_uniform_double(&localState) * (vT-vL);
    for (unsigned int i=0; i<networkSize; i++) {
        preMat[i*networkSize + id] = curand_uniform_double(&localState) * s;
        #ifdef TEST_WITH_MANUAL_FFINPUT
            // lTR works as firstInputTime
            lTR[id] = curand_uniform_double(&localState)*dInput;
        #endif
    }
}

__device__ int set_input_time(double inputTime[],
                              double dt,
                              double rate,
                              double *leftTimeRate,
                              double *lastNegLogRand,
                              curandStateMRG32k3a* __restrict__ state)
{
    int i = 0;
    double tau, dTau, negLogRand;
    tau = (*lastNegLogRand - (*leftTimeRate))/rate;
    if (tau > dt) {
        *leftTimeRate += (dt * rate);
        return i;
    } else do {
        inputTime[i] = tau;
        negLogRand = -log(curand_uniform_double(state));
        dTau = negLogRand/rate;
        tau += dTau;
        i++;
        if (i == MAX_FFINPUT_PER_DT) {
            printf("exceeding max input per dt %i\n", MAX_FFINPUT_PER_DT);
            //printf("rate = %f, lastNegLogRand = %f, leftTimeRate = %f \n", rate, *lastNegLogRand, *leftTimeRate);
            //printf("inputTime[0]: %f, inputTime[1]: %f\n", inputTime[0], inputTime[1]);
            break;
        }
    } while (tau <= dt);
    *lastNegLogRand = negLogRand;
    *leftTimeRate = (dt - tau + dTau) * rate;
    return i;
}

__host__ __device__ void evolve_g(ConductanceShape &cond,
                                  double* __restrict__ g, 
                                  double* __restrict__ h, 
                                  double* __restrict__ f,
                                  double inputTime[],
                                  unsigned int nInput, double dt, unsigned int ig)
{
    cond.decay_conductance(g, h, dt, ig); 
    for (int i=0; i<nInput; i++) {
        cond.compute_single_input_conductance(g, h, *f, dt-inputTime[i], ig);
    }
}

__device__  double step(Func_RK2* lif, double dt, double tRef, unsigned int id, double gE, double gI, double tsp[]) {
    lif->tsp = dt;
    lif->spikeCount = 0;
    // not in refractory period
    if (lif->tBack < dt) {
        // return from refractory period
        if (lif->tBack > 0.0f) {
            lif->compute_pseudo_v0(dt);
            lif->tBack = -1.0f;
        }
        __syncthreads();
        lif->runge_kutta_2(dt);
        while (lif->v > vT && lif->tBack < 0.0f) {
            // crossed threshold
            lif->tsp = lif->compute_spike_time(dt); 
            tsp[lif->spikeCount] = lif->tsp;
            lif->spikeCount++;
            lif->tBack = lif->tsp + tRef;
            if (lif->tBack < dt) {
                // refractory period ended during dt
                lif->compute_pseudo_v0(dt);
                lif->runge_kutta_2(dt);
                lif->tBack = -1.0f;
            }
        }
    } 
    if (lif->tBack >= dt) {
        // during refractory period
        lif->reset_v(); 
        lif->tBack -= dt;
    }
    if (lif->spikeCount > 1) {
        printf("#%i spiked %i in one time step %f, refractory period = %f ms, only the last tsp is recorded\n", id, lif->spikeCount, dt, tRef);
    }
    return lif->tsp;
}

__device__ void Func_RK2::runge_kutta_2(double dt) {
    double fk0 = eval0(v0);
    v_hlf = v0 + dt*fk0;
    double fk1 = eval1(v_hlf);
    v = v0 + dt*(fk0+fk1)/2.0f;
}

__device__ double LIF::compute_spike_time(double dt) {
    return (vT-v0)/(v-v0)*dt;
}

__device__ void LIF::compute_v(double dt) {
    v = compute_v1(dt, a0, b0, a1, b1, vL, tBack);
}

__device__ void LIF::compute_pseudo_v0(double dt) {
    v0 = (vL-tBack*(b0 + b1 - a1*b0*dt)/2.0f)/(1.0f+tBack*(-a0 - a1 + a1*a0*dt)/2.0f);
}

__device__ void LIF::set_p0(double gE, double gI, double gL) {
    a0 = get_a(gE, gI, gL);
    b0 = get_b(gE, gI, gL); 
}

__device__ void LIF::set_p1(double gE, double gI, double gL) {
    a1 = get_a(gE, gI, gL);
    b1 = get_b(gE, gI, gL); 
}

__device__ double LIF::eval0(double _v) {
    return eval_LIF(a0,b0,_v);
}

__device__ double LIF::eval1(double _v) {
    return eval_LIF(a1,b1,_v);
}

__device__ void LIF::reset_v() {
    v = vL;
}

__device__  double dab(Func_RK2* lif, double dt, double tRef, unsigned int id, double gE, double gI) {
    lif->tsp = dt;
    // not in refractory period
    if (lif->tBack < dt) {
        // return from refractory period
        if (lif->tBack > 0.0f) {
            lif->compute_pseudo_v0(dt);
            lif->tBack = -1.0f;
        }
        lif->runge_kutta_2(dt);
		if (lif->v > vT) {
			// crossed threshold

			lif->tsp = lif->compute_spike_time(dt);
			// dabbing not commiting, doest not reset v or recored tBack, TBD by spike correction.
		}
    } else {
        // during refractory period
        lif->reset_v(); 
    }
    return lif->tsp;
}

__global__ void compute_dV(double* __restrict__ v0,
                           double* __restrict__ dv,
                           double* __restrict__ gE,
                           double* __restrict__ gI,
                           double* __restrict__ hE,
                           double* __restrict__ hI,
                           double* __restrict__ a0,
                           double* __restrict__ b0,
                           double* __restrict__ a1,
                           double* __restrict__ b1,
                           double* __restrict__ preMat,
                           double* __restrict__ inputRate,
                           int* __restrict__ eventRate,
                           double* __restrict__ spikeTrain,
						   double* __restrict__ tBack,
                           double* __restrict__ gactVec,
                           double* __restrict__ hactVec,
                           double* __restrict__ fE,
                           double* __restrict__ fI,
                           double* __restrict__ leftTimeRate,
                           double* __restrict__ lastNegLogRand,
                           double* __restrict__ v_hlf,
                           curandStateMRG32k3a* __restrict__ state,
                           unsigned int ngTypeE, unsigned int ngTypeI, unsigned int ngType, ConductanceShape condE, ConductanceShape condI, double dt, unsigned int networkSize, unsigned int nE, unsigned long long seed, double dInput)
{
    unsigned int id = blockIdx.x * blockDim.x + threadIdx.x;
    // if #E neurons comes in warps (size of 32) then there is no branch divergence.
    LIF lif(v0[id], tBack[id]);
    double gL, tRef;
    if (id < nE) {
        tRef = tRef_E;
        gL = gL_E;
    } else {
        tRef = tRef_I;
        gL = gL_I;
    }
    /* set a0 b0 for the first step */
    double gI_t;
    double gE_t;
    // init cond E 
    gE_t = 0.0f;
    #pragma unroll
    for (int ig=0; ig<ngTypeE; ig++) {
        gE_t += gE[networkSize*ig + id];
    }
    //  cond I 
    gI_t = 0.0f;
    #pragma unroll
    for (int ig=0; ig<ngTypeI; ig++) {
        gI_t += gI[networkSize*ig + id];
    }
    lif.set_p0(gE_t, gI_t, gL);
    // storing for spike correction
    a0[id] = lif.a0;
    b0[id] = lif.b0;
    /* Get feedforward input */
    // consider use shared memory for dynamic allocation
    double inputTime[MAX_FFINPUT_PER_DT];
    curandStateMRG32k3a localState = state[id];
    int nInput;
    #ifdef TEST_WITH_MANUAL_FFINPUT
        nInput = 0;
        if (leftTimeRate[id] < dt) {
            inputTime[nInput] = leftTimeRate[id];
            nInput++;
            double tmp = leftTimeRate[id] + dInput;
            while (tmp < dt){
                inputTime[nInput] = tmp;
                nInput++;
                tmp += dInput;
            }
            leftTimeRate[id] = tmp - dt;
        } else {
            leftTimeRate[id] -= dt;
        }
    #else
        nInput = set_input_time(inputTime, dt, inputRate[id], &(leftTimeRate[id]), &(lastNegLogRand[id]), &localState);
    #endif
    //__syncwarp();
    // return a realization of Poisson input rate
    eventRate[id] = nInput;
    // update rng state 
    state[id] = localState;
    /* evolve g to t+dt with ff input only */
    unsigned int gid;
    gE_t = 0.0f;
    #pragma unroll
    for (int ig=0; ig<ngTypeE; ig++) {
        gid = networkSize*ig + id;
        double g_i = gE[gid];
        double h_i = hE[gid];
        double f_i = fE[gid];
        evolve_g(condE, &g_i, &h_i, &f_i, inputTime, nInput, dt, ig);
        //__syncwarp();
        gE_t += g_i;
        gE[gid] = g_i;
        hE[gid] = h_i;
        // for learning
        //fE[gid] = f_i;
    }
    //printf("id %i, exc cond ready.\n",id);
    gI_t = 0.0f;
    /* no feed-forward inhibitory input (setting nInput = 0) */
    #pragma unroll
    for (int ig=0; ig<ngTypeI; ig++) {
        gid = networkSize*ig + id;
        double g_i = gI[gid];
        double h_i = hI[gid];
        double f_i = fI[gid];
        evolve_g(condI, &g_i, &h_i, &f_i, inputTime, 0, dt, ig);
        //__syncwarp();
        gI_t += g_i;
        gI[gid] = g_i;
        hI[gid] = h_i;
        // for learning
        //fI[gid] = f_i;
    }
    lif.set_p1(gE_t, gI_t, gL);
    // storing for spike correction
    a1[id] = lif.a1;
    b1[id] = lif.b1;
    // rk2 step
    spikeTrain[id] = dab(&lif, dt, tRef, /*the last 2 args are for deugging*/ id, gE_t, gI_t);
    v_hlf[id] = lif.v_hlf;
	//tBack[id] = lif.tBack; // TBD after spike correction, comment this line if SSC is naive.
    if (lif.v < vI) {
		printf("#%i something is off gE = %f, gI = %f, v0 = %f, v1/2 = %f, v = %f, a0 = %f, b0 = %f, a1 = %f, b1 = %f\n", id, gE_t, gI_t, lif.v0, lif.v_hlf, lif.v, lif.a0, lif.b0, lif.a1, lif.b1);
        lif.v = vI;
    }   
    if (lif.tsp < 0.0f) {
		printf("#%i backfired v0 = %f, v1/2 = %f, v = %f, tsp = %f\n", id, lif.v0, lif.v_hlf, lif.v, lif.tsp);
        assert(lif.tsp >= 0.0f);
    }
	//if (id == 0 || id == nE) {
	//	printf("#%i: v old = %f, v est = %f\n", id, lif.v0, lif.v);
	//	printf("#%i: tsp = %f, tb = %f\n", id, lif.tsp, tBack[id]);
    //    printf("#%i: gE = %f, gI = %f\n", id, gE_t, gI_t);
	//}
	dv[id] = lif.v - lif.v0; // TBD after spike correction to reset etc.
}

__global__ void correct_spike(bool*   __restrict__ not_matched,
                              double* __restrict__ spikeTrain,
                              double* __restrict__ v_hlf,
                              double* __restrict__ v0,
                              double* __restrict__ dv,
                              double* __restrict__ a0,
                              double* __restrict__ b0,
                              double* __restrict__ a1,
                              double* __restrict__ b1,
                              double* __restrict__ vnew,
                              double* __restrict__ preMat,
                              double* __restrict__ tBack,
                              unsigned int* __restrict__ nSpike,
                              unsigned int ngTypeE, unsigned int ngTypeI, ConductanceShape condE, ConductanceShape condI, double dt, unsigned int poolSizeE, unsigned int poolSize) 
{
    unsigned int id = blockIdx.x * blockDim.x + threadIdx.x;
    bool local_not_matched = false;
    double v_new = vL;
    double tsp = spikeTrain[id];
    double tRef;
    if (id < poolSizeE) {
        tRef = tRef_E;
    } else {
        tRef = tRef_I;
    }
    double vhlf =  v_hlf[id];
    double minTsp_i = tsp;
    double dvE = vhlf - vE;
    double dvI = vhlf - vI;
    double deltaV = dv[id]; // init with old dv to be new dv
    double dg = 0.0;
    double dgV = 0.0;
    unsigned ns = nSpike[id];
    for (unsigned int i = 0; i < poolSizeE; i++) {
        double tsp_i = spikeTrain[i];  // possible share_mem optimization
        if (tsp > tsp_i) {
            if (tsp_i < minTsp_i) {
                minTsp_i = tsp_i;
            }
            double dtij = dt - tsp_i;
            #pragma unroll
            for (unsigned int ig = 0; ig < ngTypeE; ig++) {
                double g = preMat[i*poolSize + id] * condE.dg(dtij, ig);
                dg += g;
                dgV += g*vE;
                deltaV += g * dvE;
            }
        }
    }
    for (unsigned int i = poolSizeE; i < poolSize; i++) {
        double tsp_i = spikeTrain[i]; // possible share_mem optimization
        if (tsp > tsp_i) {
            double dtij = dt - tsp_i;
            #pragma unroll
            for (unsigned int ig = 0; ig < ngTypeI; ig++) {
                double g = preMat[i*poolSize + id] * condI.dg(dtij, ig);
                dg += g;
                dgV += g*vI;
                deltaV += g * dvI;
            }
        }
    }
    double v0i = v0[id];
    double old_tsp = tsp;
    tsp = dt;
    v_new = v0i + deltaV;
    if (v_new > vT) {
        tsp = dt * (vT - v0i) / deltaV;
        if (tsp < minTsp_i) {
            tsp = minTsp_i;
        }
        if (tsp + tRef > dt) {
            v_new = vL; 
        } else {
            while(tsp + tRef > dt) {
                v_new = compute_v1(dt, a0[id], b0[id], a1[id] + dg, b1[id] + dgV, vL, tsp + tRef);
                tsp = dt*(vT-v0i)/deltaV;
                assert(tsp>=0.0f);
            }
        }
    }
    assert(tsp>=0.0f);
    spikeTrain[id] = tsp;
    if (tsp == dt && dt - old_tsp > EPS || dt - tsp > EPS && old_tsp == dt) {
        local_not_matched = true;
    }
    __syncthreads();
    not_matched[id] = local_not_matched;
    vnew[id] = v_new;
}

__global__ void prepare_cond(double* __restrict__ tBack,
                             double* __restrict__ spikeTrain,
                             double* __restrict__ gactVec,
                             double* __restrict__ hactVec,
                             unsigned int* __restrict__ nSpike,
                             ConductanceShape cond, double dt, unsigned int ngType, unsigned int offset, unsigned int networkSize) 
{
    unsigned int id = offset + blockIdx.x * blockDim.x + threadIdx.x;
    //setup acting vectors
    double g_end, h_end;
    double tsp = spikeTrain[id];
    double tB = -1.0f;
    if (tsp < dt) {
        if (offset == 0) {
            tB = tsp + tRef_E - dt;
        } else {
            tB = tsp + tRef_I - dt;
        }
    }
    __syncthreads();
    tBack[id] = tB;
    #pragma unroll
    for (int ig=0; ig<ngType; ig++) {
        g_end = 0.0f;
        h_end = 0.0f;
        if (tsp < dt) {
            unsigned int ns = nSpike[id];
            cond.compute_single_input_conductance(&g_end, &h_end, 1.0f, dt-tsp, ig);
            g_end *= ns;
            h_end *= ns;
        }
        unsigned int gid = networkSize*ig + id;
        gactVec[gid] = g_end;
        hactVec[gid] = h_end;
    }
}
