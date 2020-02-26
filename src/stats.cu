#include "stats.h"
using namespace std;

__global__
pixelize(
        Float* __restrict__ array,
        double* __restrict__ x,
        double* __restrict__ y,
        Float* __restrict__ frame,
        Size width, Size height) 
{
}

// From nChunks of [chunkSize, ngTypeE+ngTypeI, blockSize] -> [ngTypeE+ngTypeI, nV1], where nV1 = nChunk*chunkSize*blockSize
void reshape_chunk_and_write(Float chunk[], ofstream fRawData, Size maxChunkSize, Size remainChunkSize, Size nChunk, Size nE, Size nI, Size nV1) {
    PosIntL offset = 0;
    size_t gSize = nV1*(ngTypeE+ngTypeI);
    Float *flatten = new Float[gSize];
    Size chunkSize = maxChunkSize;
    for (PosInt i=0; i<nChunk; i++) {
        if (i == nChunk-1) chunkSize = remainChunkSize;
        for (PosInt j=0; j<nE; j++) {
            PosIntL fid = i*maxChunkSize*blockSize + j*nV1;
            for (PosInt k=0; k<chunkSize*blockSize; k++) {
                flatten[j*nV1 + i*blockSize + k] = chunk[offset];
                offset++;
            }
        }
        for (PosInt j=0; j<nI; j++) {
            PosIntL fid = nE*nV1 + i*maxChunkSize*blockSize + j*nV1;
            for (PosInt k=0; k<chunkSize*blockSize; k++) {
                flatten[fid + k] = chunk[offset];
                offset++;
            }
        }
        assert(offset == (i+1)*maxChunkSize*blockSize*(nE+nI));
    }
    fRawData.write((char*) flatten, gSize*sizeof(Float));
    delete []flatten;
}

void getLGN_V1_surface(vector<PosInt> &xy, vector<vector<PosInt>> &LGN_V1_ID, PosInt* surface, Size max_LGNperV1, Size nLGN) {
    Size nV1 = LGN_V1_ID.size();
    for (PosInt i=0; i<nV1; ++) {
        for (PosInt j=0; j<LGN_V1_ID[i].size(); j++) {
            PosInt xid = i*max_LGNperV1 + j;
            surface[xid] = xy[LGN_V1_ID[i][j]]; // x
            PosInt yid = nV1*max_LGNperV1 + xid;
            surface[yid] = xy[nLGN + LGN_V1_ID[i][j]];
        }
    }
}
