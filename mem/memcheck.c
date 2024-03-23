#include <fcntl.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <time.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <string.h>
#include <time.h>

char FILENAME[1024] = {0};
int expOFFSET = 0;
char* buf = NULL;
void *addr;
int *mark;
unsigned long num = 0;
#define bSIZE 4096
#define PROTECTION (PROT_READ | PROT_WRITE)
#define FLAGS (MAP_SHARED |MAP_FIXED)

int ww(unsigned long index)
{
    int fd,n;
    char *path = FILENAME;
    int i = 0;
    int off = 0;
    int ret;
    int exp = index % 0xff;
    unsigned long foff = index * bSIZE;
    //printf("WW: index %lx exp %lx\n",index, exp);
    char *seek;

    seek = foff + addr;
    //printf("seek is %p\n", seek);
    while (i < bSIZE) {
        //printf("write: the content is %x addr %p\n",exp, (char *)(seek+i));
        *(seek+i) = exp;
        ++i;
    }
}

int rr(unsigned long index)
{
    int fd,n;
    char *path = FILENAME;
    int i = 0;
    int off = 0;
    int ret;
    int exp = index % 0xff;
    unsigned long foff = index * bSIZE;
    char *seek;
    //printf("RR: index %lx exp %lx\n",index, exp);

    
    seek = foff + addr;
    while (i < bSIZE) {
        //printf("read: the content is %x addr %p\n",*(seek+i), (char *)(seek+i));
        if (*(seek + i) != (char)exp) {
            printf("WRONG %x should %x\n",*(seek+i),exp);
            exit(1);
        }
        ++i;
    }
        num++;
        if ((num % 1000) == 0) {
            printf("check pages ok %d\n",num);
        }
}

int main(int argc, char* argv[])
{
    if (argc < 3) {
        printf("file size ? file name ?\n");
        exit(1);
    }
    int fd;
    unsigned long fsize;
    unsigned long i, index;
    strcat(FILENAME,argv[2]);
    char *path = FILENAME;
    unsigned long pages;

    printf("test file: %s\n",FILENAME);
    fsize = atoi(argv[1]);
    printf("fsize: %d\n", fsize);

    srand((unsigned)time(NULL));
    //MB
    pages = fsize * 1024 * 1024 / 4096;
    mark = (int *)malloc(pages * sizeof(int));
    printf("file pages: %d\n", pages);
    fsize = fsize << 20;
    fd = open(path, O_CREAT | O_RDWR, 0755);
    posix_memalign((void**)&buf, 2097152, fsize);
    addr = mmap(buf, fsize, PROTECTION, FLAGS, fd, 0);
    printf("head addr is %p\n", addr);
    printf("tail addr is %p\n", addr + fsize);
    if (addr == MAP_FAILED) {
        perror("mmap");
        unlink(FILENAME);
        exit(1);
    }

    while(1){
        for(i=0; i < 4096; ++i) {
            index = rand() % pages;
            mark[index] = 1;
            ww(index);
        }

        for(i=0; i < 4096; ++i) {
            index = rand() % pages;
            if (mark[index] == 1) {
                rr(index);
            } else {
                //printf("next\n");
            }
        }
    }
}
