#include "connect.h"
#include <cassert>
#include "../util/cuda_util.h"
#include "../types.h"

// TODO: randomize neuronal attributes by using distribution, strength x number of con. should be controlled
__global__ void initialize(curandStateMRG32k3a* __restrict__ state,
                           Size*  __restrict__ preType,
                           Float* __restrict__ rden,
                           Float* __restrict__ raxn,
                           Float* __restrict__ dden,
                           Float* __restrict__ daxn,
                           Float* __restrict__ preS_Type,
                           Float* __restrict__ preP_Type,
                           Size*  __restrict__ preN,
						   Int* __restrict__ preFixType, // nHierarchy * networkSize
                           initialize_package &init_pack, unsigned long long seed, Size networkSize, Size nType, Size nArchtype, Size nHierarchy) {
    Size id = blockIdx.x * blockDim.x + threadIdx.x;
    curand_init(seed, id, 0, &state[id]);
   	Size type; 
	// determine the arch neuronal type and its properties
	#pragma unroll
    for (Size i=0; i<nArchtype; i++) {
        if (init_pack.typeAccCount[i] < threadIdx.x && threadIdx.x < init_pack.typeAccCount[i+1]) {
			type = i;
            rden[id] = init_pack.rden[i];
            raxn[id] = init_pack.raxn[i];
            dden[id] = init_pack.dden[i];
            daxn[id] = init_pack.daxn[i];
            preN_type[id] = init_pack.preTypeN[i];
        }
	}
	// determine subTypes
	Size nType_remain = nType/nArchtype;
	type += nType_remain * type;
	for (Size i=1; i<nHierarchy; i++) {
		Size subType = preFixType[i*networkSize + id];
 		nType_remain /= init_pack.nTypeHierarchy[i];
		type += nType_remain * subType;
    }
    preType[id] = type;
	for (Size i=1; i<nType; i++) {
		Size tid = i*networkSize+id;
		Size ttid = i*nType + type;
    	preS_type[tid] = init_pack.sTypeMat[ttid];
    	preP_type[tid] = init_pack.pTypeMat[ttid];
	}
}

__device__ 
__forceinline__
Float tri_cos(Float a, Float b, Float c) {
    return (a*a + b*b - c*c)/(2*a*b);
}

//__device__ Float seg(Float cosine, Float radius) {
//    return arccos(cosine)/(radius*radius);
//}

//__device__ Float chord(Float radius, Float cosine) {
//    Float r2 = radius*radius;
//    Float cos2 = cosine*cosine;
//    return square_root(r2- cos2*r2) * radius*cosine;
//}

__device__ 
__forceinline__
Float area(Float raxn, Float rden, Float d) {
    Float cos_theta_axn = tri_cos(raxn, d, rden);
	Float cos_theta_den = tri_cos(rden, d, raxn);

    Float theta_axn = arccos(cos_theta_axn);
    Float theta_den = arccos(cos_theta_den);

    Float sin_theta_axn = sine(theta_axn);
    Float sin_theta_den = sine(theta_den);

    return (theta_axn-sin_theta_axn*cos_theta_axn)*raxn*raxn 
         + (theta_den-sin_theta_den*cos_theta_den)*rden*rden;
}

// co-occupied area of the presynaptic axons / dendritic area
__device__ 
__forceinline__
Float connect(Float distance, Float raxn, Float rden, bool gaussian_profile) {
	Float weight;
	if (gaussian_profile) {
		Float spread = raxn*raxn + rden*rden;
		weight = exponential(distance*distance/spread)/(M_PI*spread);
	} else {
    	weight = 0.0;
    	if (raxn + rden > distance && distance > abs(raxn - rden)) {
    	    weight = area(raxn, rden, distance)/(M_PI*rden*rden); // conn. prob. is defined by the presynaptic point of view
    	} else if (distance <= abs(raxn - rden)) {
    	    weight = 1.0;
    	}
	}
    return weight;
}

__global__ 
void cal_blockPos(double* __restrict__ pos,
                  Float* __restrict__ block_x,
                  Float* __restrict__ block_y,
                  Size networkSize) {
    __shared__ double x[warpSize];
    __shared__ double y[warpSize];
    Size id = blockDim.x*blockIdx.x + threadIdx.x;
    block_reduce<double>(x, pos[id]);
    if (threadIdx.x == 0) {
        block_x[blockIdx.x] = static_cast<Float>(x[0]/blockSize);
    }
    block_reduce<double>(y, pos[networkSize + id]);
    if (threadIdx.x == 0) {
        block_y[blockIdx.x] = static_cast<Float>(y[0]/blockSize);
    }
}

__device__ 
__forceinline__
void compare_distance_with_neighbor_block(Size* __restrict__ iNeighbor, 
													 Float bx,
													 Float by,
													 Float* __restrict__ block_x, 
													 Float* __restrict__ block_y, 
													 Size* __restrict__ neighborBlockId, 
													 Size offset, Size maxNeighborBlock, Float radius) {
    Size blockId = offset + threadIdx.x;
    Float x = block_x[blockId] - bx;
    Float y = block_y[blockId] - by;
    Float distance = square_root(x*x + y*y);
    if (distance < radius && blockId != blockIdx.x) {
        Size current_index = atomicAdd(iNeighbor, 1);
		if (current_index >= maxNeighborBlock) {
		}
        neighborBlockId[maxNeighborBlock*blockIdx.x + current_index] = blockId;
    }
}

__global__ 
void get_neighbor_blockId(Float* __restrict__ block_x,
                                     Float* __restrict__ block_y,
                                     Size* __restrict__ neighborBlockId,
                                     Size* __restrict__ nNeighborBlock,
                                     Float max_radius, Size maxNeighborBlock) {
    __shared__ Size iNeighbor[1];
    iNeighbor[0] = 0;
    Float bx = block_x[blockIdx.x]; // center of the target block
    Float by = block_y[blockIdx.x];
    tid = threadIdx.y*blockDim.x + threadIdx.x;
    Size nblock = gridDim.x;
    Size nPatch = nblock/nblockSize;
    Size remain = nblock%blockSize;

    Size offset = 0;
    for (Size iPatch = 0; iPatch < nPatch+1; iPatch++) {
        if (iPatch < nPatch || tid < remain) {
            compare_distance_with_neighbor_block(iNeighbor, bx, by, block_x, block_y, neighborBlockId, offset, maxNeighborBlock, max_radius);
        }
        if (iPatch < nPatch) {
            offset += blockSize;
        }
    }
    __syncthreads();
    if (tid == 0) {
        nNeighbor = iNeighbor[0]+1;
        if (nNeighbor > maxNeighborBlock) {
            printf("actual nNeighbor = %d > %d (preserved)\n", nNeighbor, maxNeighborBlock);
		    assert(nNeighbor <= maxNeighborBlock);
        }
        nNeighborBlock[blockIdx.x] = nNeighbor;
    }
}

__global__ 
void generate_connections(double* __restrict__ pos,
                          Float* __restrict__ preS_type,
                          Float* __restrict__ preP_type,
                          Size* __restrict__ preN_type,
                          Size* __restrict__ neighborBlockId,
                          Size* __restrict__ nNeighborBlock,
                          Float* __restrict__ rden,
                          Float* __restrict__ raxn,
                          Float* __restrict__ conMat, //within block connections
                          Float* __restrict__ delayMat,
                          Float* __restrict__ conVec, //for neighbor block connections
                          Float* __restrict__ delayVec, //for neighbor block connections
                          Size* __restrict__ vecID,
                          Size* __restrict__ nVec,
                          Size* __restrict__ preTypeConnected,
                          Size* __restrict__ preTypeAvail,
                          Float* __restrict__ preTypeStrSum,
                          Size* __restrict__ preType,
                          Float* __restrict__ dden,
                          Float* __restrict__ daxn,
                          curandStateMRG32k3a* __restrict__ state,
                          Size networkSize, Size maxDistantNeighbor, Size maxNeighborBlock, Float speedOfThought, Size nType, bool gaussian_profile) {
    __shared__ double x1[blockSize];
    __shared__ double y1[blockSize];
    __shared__ Size ipreType[blockSize];
    Size offset = blockIdx.x*blockSize;
    Size id = offset + threadIdx.x;
    Size nb = nNeighborBlock[blockIdx.x]*blockSize;
    Size* sumConType = new Size[nType];
    Size* sumType = new Size[nType];
    Float* sumStrType = new Size[nType];
    Float* tempNeighbor = new Float[nb];
    curandStateMRG32k3a localState = state[id];
    ipreType[threadIdx.x] = preType[id];
    double x0 = pos[id];
    double y0 = pos[networkSize + id];
    Float rd = rden[id];
    #pragma unroll
    for (Size i=0; i<nType; i++) {
        sumConType[i] = 0;
        sumStrType[i] = 0;
        sumType[i] = 0;
    }
    Float sumP = 0.0;
    x1[threadIdx.x] = x0;
    y1[threadIdx.x] = y0;
    __syncthreads();
    //============= collect p of all ==========
    // withhin block
    #pragma unroll
    for (Size i=0; i<blockSize; i++) {
        //matrix, indexed within one block
        Size ipre = blockIdx.x*blockSize + i;
        //type vector, indexed across the network
        double x = x1[i] - x0;
        double y = y1[i] - y0;
        Float ra = raxn[ipre];
        Float distance = static_cast<Float>(square_root(x*x + y*y));
		// weight from area
        Float p = connect(distance, ra, rd, gaussian_profile);

        if (p > 0) {
            unsigned long bid = ipre*blockSize + threadIdx.x;
            Size ip = ipreType[i];
            sumType[ip] += 1;
			// update weight with density of axon dendrites and preference over type
            p = p * daxn[ipre] * dden[id] * preP_type[ip*networkSize + id];
            sumP += p;
            conMat[bid] = p;
            delayMat[bid] = distance/speedOfThought;
        }
    }
    for (Size i=0; i<nNeighborBlock[blockIdx.x]; i++) {
        Size bid = neighborBlockId[maxNeighborBlock*blockIdx.x + i];
        #pragma unroll
        for (Size j=0; j<blockSize; j++) {
            // index in the network
            Size ipre = bid*blockSize + j;
            // index in conVec
            double x = pos[ipre] - x0;
            double y = pos[networkSize+ipre] - y0;
            Float ra = raxn[ipre];
            Float distance = static_cast<Float>(square_root(x*x + y*y));
            Float p = connect(distance, ra, rd);
            //if (id == 7072 && p == 0) {
            //    printf("o:(%f,%f) <- %f, a:%f, d:%f, p=%f\n", x0, y0, distance, ra, rd, p);
            //    printf("sumType > 0\n");
            //}
            unsigned long tid = i*blockSize + j;
            if (p > 0) {
                Size ip = preType[ipre];
                sumType[ip] += 1;
                p = p * daxn[ipre] * dden[id] * preP_type[ip*networkSize+id];
                sumP += p;
                tempNeighbor[tid] = p;
            } else {
            	tempNeighbor[tid] = 0;
			}
        }
    }
    __syncwarp();

    //============= redistribute p of all ==========
    #pragma unroll
    for (Size i=0; i<blockSize; i++) {
        Size ipre = blockIdx.x*blockSize + i;
        unsigned long bid = ipre*blockSize + threadIdx.x;
        Size ip = ipreType[i];
        Float str = preS_type[ip*networkSize+id];
        Float p = conMat[bid]/sumP[ip]*preN[id];
        Float xrand = uniform(&localState);
        if (xrand < p) {
            if (p > 1) {
                str = str*p;
            }
            p = str;
            sumConType[ip] += 1;
            sumStrType[ip] += str;
        } else {
            p = 0;
        }
        __syncwarp();
        conMat[bid] = p;
    }
    
    Size nid = 0;
    for (Size i=0; i<nNeighborBlock[blockIdx.x]; i++) {
        Size bid = neighborBlockId[maxNeighborBlock*blockIdx.x + i];
        #pragma unroll
        for (Size j=0; j<blockSize; j++) {
            Size ipre = bid*blockSize + j;
            unsigned long tid = i*blockSize + j;
            Size ip = preType[ipre];
            Float str = preS_type[ip*networkSize+id];
            Float p = tempNeighbor[tid]/sumP*preN[id];
            Float xrand = uniform(&localState);
            if (xrand < p) {
                if (p > 1) {
                    str = str*p;
                }
                sumConType[ip] += 1;
                sumStrType[ip] += str;
                vecID[maxDistantNeighbor*id + nid] = ipre;
                conVec[maxDistantNeighbor*id + nid] = str;
                double x = pos[ipre] - x0;
                double y = pos[networkSize+ipre] - y0;
				Float distance = static_cast<Float>(square_root(x*x + y*y));
                delayVec[maxDistantNeighbor*id + nid] = distance/speedOfThought;
                nid += 1;
                if (nid > maxDistantNeighbor) {
                    printf("set bigger maxDistantNeighbor, currently %u\n", maxDistantNeighbor);
                    assert(nid <= maxDistantNeighbor);
                }
            }
        }
    }
    nVec[id] = nid;
    #pragma unroll
    for (Size i=0; i<nType; i++) {
        preTypeConnected[i*networkSize + id] = sumConType[i];
        preTypeAvail[i*networkSize + id] = sumType[i];
        preTypeStrSum[i*networkSize + id] = sumStrType[i];
    }
    delete []sumConType;
    delete []sumType;
    delete []sumStrType;
    delete []tempNeighbor;
}
