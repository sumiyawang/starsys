./hot 16384 4096 //malloc and write 16G and loop write memory 0~4G

./stream12 //stream 12G test
./stream24

gcc -mcmodel=large -fopenmp -D_OPENMP -DSTREAM_ARRAY_SIZE=1073741824 stream.c -o stream -O3
