#include <fstream>
#include <sstream>
#include <string>
#include <iostream>
#include <cassert>
#include <ctime>
#include <cmath>
#include <random>
#include <fenv.h>
#include <algorithm>
#include <boost/program_options.hpp>

#include "connect.h"
#include "../types.h"
#include "../util/po.h" // custom validator for reading vector in the configuration file
#include "../util/util.h"

#define nFunc 2

__host__ __device__
Float ODpref(Float post, Float pre, Float r) { // ocular dominance
    Float p;
    if (post*pre < 0) {
        p = r;
    } else {
        p = 1-r;
    }
    return p; 
}
__device__ pFeature p_OD = ODpref;

__host__ __device__
Float OPpref(Float post, Float pre, Float r) { // orientation preference
	Float p;
	if (r > 0) {
    	Float dp = post - pre;
    	if (abs(dp) > M_PI/2) {
    	    dp += copyms(M_PI, -dp);
    	}
    	Float sig = M_PI/r; // set spread here
    	Float A = square_root(2*M_PI);
    	p = exponential(-dp*dp/(2*sig*sig))/(A*sig);
	} else {
		p = 1/M_PI;
	}
    return p; 
}
__device__ pFeature p_OP = OPpref;

__host__ __device__
Float pass(Float post, Float pre, Float r) {
    return 1.0;
}
__device__ pFeature p_pass = pass;

__device__ __constant__ pFeature pref[nFunc];

void initializePreferenceFunctions(Size nFeature) {
    pFeature h_pref[nFunc];
    if (nFunc != nFeature) {
        std::cout << "number of preference functions = " << nFunc << ", is inconsistent with the number of the features: " << nFeature << "\n";
        assert(nFunc == nFeature);
    }
    checkCudaErrors(cudaMemcpyFromSymbol(&h_pref[0], p_OD, sizeof(pFeature), 0, cudaMemcpyDeviceToHost));
    checkCudaErrors(cudaMemcpyFromSymbol(&h_pref[1], p_OP, sizeof(pFeature), 0, cudaMemcpyDeviceToHost));
    checkCudaErrors(cudaMemcpyToSymbol(pref, h_pref, nFunc*sizeof(pFeature), 0, cudaMemcpyHostToDevice));
}

void read_wLGN(std::string filename, Float sSum[], Float sSumMin[], Float sSumMax[], Size typeAcc[], Size nType, Size nblock, bool print) {
    std::ifstream input_file;
    input_file.open(filename, std::fstream::in | std::fstream::binary);
    if (!input_file) {
        std::string errMsg{ "Cannot open or find " + filename + "\n" };
        throw errMsg;
    }
    Size nList, maxList;
    input_file.read(reinterpret_cast<char*>(&nList), sizeof(Size));
    input_file.read(reinterpret_cast<char*>(&maxList), sizeof(Size));
	if (print) {
		std::cout << "nList = " << nList << "\n";
		std::cout << "maxList = " << maxList << "\n";
	}

    Float *array = new Float[nList*maxList];
    Size *nTypeCount = new Size[nType];
    for (PosInt i=0; i<nType; i++) {
        sSumMax[i] = 0.0;
        sSumMin[i] = maxList;
        if (i == 0) {
            nTypeCount[i] = typeAcc[i];
        } else {
            nTypeCount[i] = typeAcc[i] - typeAcc[i-1];
        }
        nTypeCount[i] *= nblock;
    }
    for (PosInt i=0; i<nList; i++) {
        Size listSize;
        input_file.read(reinterpret_cast<char*>(&listSize), sizeof(Size));
        input_file.read(reinterpret_cast<char*>(&array[i*maxList]), listSize * sizeof(Float));
        for (PosInt j=0; j<listSize; j++) {
            sSum[i] += array[i*maxList+j];
        }
        PosInt k = i%MAX_BLOCKSIZE;
        for (PosInt j = 0; j<nType; j++) {
            if (k<typeAcc[j]) {
                k = j;
                break;
            }
        }
        if (sSum[i] > sSumMax[k]) {
            sSumMax[k] = sSum[i];
        }
        if (sSum[i] < sSumMin[k]) {
            sSumMin[k] = sSum[i];
        }
        if (print) {
            std::cout << i << ", type " << k << " sum " << sSum[i] << ": ";
            for (PosInt j=0; j<listSize; j++) {
                std::cout << array[i*maxList + j];
                if (j == listSize-1) std::cout << "\n";
                else std::cout << ", ";
            }
        }
    }
    delete []array;
    delete []nTypeCount;
    input_file.close();
}

void read_LGN_V1(std::string filename, Size nLGN_V1[], Size nLGN_V1_Max[], Size typeAcc[], Size nType) {
    std::ifstream input_file;
    input_file.open(filename, std::fstream::in | std::fstream::binary);
    if (!input_file) {
        std::string errMsg{ "Cannot open or find " + filename + "\n" };
        throw errMsg;
    }
    Size nList, maxList;
    input_file.read(reinterpret_cast<char*>(&nList), sizeof(Size));
    input_file.read(reinterpret_cast<char*>(&maxList), sizeof(Size));

    Float *array = new Float[nList*maxList];
    for (PosInt i=0; i<nType; i++) {
        //nLGN_V1Mean[i] = 0.0;
        nLGN_V1_Max[i] = 0.0;
    }
    for (PosInt i=0; i<nList; i++) {
        Size listSize;
        input_file.read(reinterpret_cast<char*>(&listSize), sizeof(Size));
		nLGN_V1[i] = listSize;
        input_file.read(reinterpret_cast<char*>(&array[i*maxList]), listSize * sizeof(Float));
        PosInt k = i%MAX_BLOCKSIZE;
        for (PosInt j = 0; j<nType; j++) {
            if (k<typeAcc[j]) {
                k = j;
                break;
            }
        }
        if (nLGN_V1[i] > nLGN_V1_Max[k]) {
            nLGN_V1_Max[k] = nLGN_V1[i];
        }
    }
    delete []array;
    input_file.close();
}
