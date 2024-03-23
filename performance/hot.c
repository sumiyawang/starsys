#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define DPAGESIZE 1 << 20
#define DATAMAX DPAGESIZE >> 3


unsigned long PAGESUM;
unsigned long hot = 0;
int times;

int sort()
{

        unsigned long *a = (unsigned long *) malloc (PAGESUM << 20);
        struct timeval start, end;
        unsigned long total = PAGESUM << 20;
        printf("p: %p\n",a);
        int count = 0;
        while(1) {
            if (count!=0)
                total = (unsigned long)hot * 1024 * 1024;
            //printf("total: %ld\n",total);
            gettimeofday(&start,NULL);
            memset(a, 0x7, total);
            gettimeofday(&end,NULL);
            long interval = 1000000*(end.tv_sec - start.tv_sec) + (end.tv_usec - start.tv_usec);
            //printf("write time: %f\n",interval/1000.0/1000.0);
            printf("write speed = %f MB/s \n", (double)(total/(interval/1000.0/1000.0))/(1<<20));
            unsigned long np = 0;
            if (count!=0) {
                gettimeofday(&start,NULL);
                char *tmp = a;
                int ret;
                while(np < hot*1024/4/2) {
                    ret = memcmp(tmp ,tmp + 4096, 4096);
                    if(ret) {
                        printf("memory go die\n");
                        exit(-1);
                    }
                    tmp = tmp + 8192;
                    ++np;
                }
                gettimeofday(&end,NULL);
                long interval = 1000000*(end.tv_sec - start.tv_sec) + (end.tv_usec - start.tv_usec);
                //printf("read time: %f\n",interval/1000.0/1000.0);
                printf(" read speed = %f MB/s \n", (double)(total/(interval/1000.0/1000.0))/(1<<20));
            }
            
            ++count;
            sleep(3);
        }
        return 0;
}

int main(int argc,char *argv[])
{
        int ret;
        unsigned long start;
        unsigned long end;
        long run_time;
        double rate;
        int times;
        int count;

        PAGESUM=1;
        if (argc == 2) {
            PAGESUM = atoi(argv[1]);
        } else if (argc == 3) {
            PAGESUM = atoi(argv[1]);
            hot = atoi(argv[2]);
        }
        printf("total : %ld MB\n",PAGESUM);
        printf("hot: %ld MB\n",hot);
        sort();
        sleep(200000);
}
