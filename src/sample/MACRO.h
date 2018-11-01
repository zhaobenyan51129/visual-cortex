#ifndef MACRO_H
#define MACRO_H

#define MAX_FFINPUT_PER_DT 10 // dt in ms
#define HALF_MEMORY_OCCUPANCY 1 // in Mb

#define CUDA_ERROR_CHECK
//#define CUDA_DEEP_ERROR_CHECK

#define CUDA_CALL(err) __cudaSafeCall(err, __FILE__, __LINE__)
#define CUDA_CHECK() __cudaCheckError( __FILE__, __LINE__)
#define d_CUDA_CHECK() __cudaDeviceCheckError( __FILE__, __LINE__)

__forceinline__  void __cudaSafeCall(cudaError_t err, const char *file, const int line) {
#ifdef CUDA_ERROR_CHECK
    if (err != cudaSuccess) {
        fprintf(stderr,"CUDA Error at %s:%d : %s\n", file, line, 
                cudaGetErrorString(err));
        exit(EXIT_FAILURE);
    }
#endif
}

__forceinline__  void __cudaCheckError( const char *file, const int line )
{
#ifdef CUDA_ERROR_CHECK
#ifdef CUDA_DEEP_ERROR_CHECK
    cudaError err = cudaDeviceSynchronize();
#else
    cudaError err = cudaGetLastError();
#endif

    if ( cudaSuccess != err )
    {
        fprintf(stderr,"CUDA Error at %s:%i : %s\n", file, line, 
                cudaGetErrorString(err));
        exit(EXIT_FAILURE);
    }

#endif
}

__forceinline__  __device__ void __cudaDeviceCheckError( const char *file, const int line )
{
#ifdef CUDA_ERROR_CHECK
    cudaError err = cudaGetLastError();
    if ( cudaSuccess != err )
    {
        printf("CUDA Error at %s:%i : %s\n", file, line, 
                cudaGetErrorString(err));
    }
#endif
}

#endif
