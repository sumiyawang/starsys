#include <fcntl.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <time.h>

char FILENAME[1024] = {0};
int expOFFSET = 0;
#define bSIZE 4096
int ww(unsigned long index, int exp)
{
    int fd,n;
    char* buf = NULL;
    char *path = FILENAME;
    int i = 0;
    int off = 0;
    int ret;
    unsigned long foff = index * bSIZE;
    //printf("index %d expOFFSET %d exp %d\n",index,expOFFSET,exp);
    
    fd = open(path,O_RDWR|O_DIRECT|O_CREAT);
    posix_memalign((void**)&buf, getpagesize(), bSIZE);
    while (i < bSIZE) {
        buf[i++] = (char)exp;
    }
    //printf("write: the content is %s\n",buf);
    
    i = lseek(fd, foff, SEEK_SET);
    n = write(fd,buf,bSIZE);
    ret = fsync(fd);
    close(fd);
    free(buf);
}

int rr(unsigned long index, int exp)
{
    int fd,n;
    char* buf = NULL;
    char *path = FILENAME;
    int i = 0;
    int off = 0;
    int ret;
    unsigned long foff = index * bSIZE;
    //printf("index %d expOFFSET %d exp %d\n",index,expOFFSET,exp);
    
    fd = open(path,O_RDWR|O_DIRECT);
    posix_memalign((void**)&buf, getpagesize(), bSIZE);
    i = lseek(fd, foff, SEEK_SET);
    n = read(fd, buf, bSIZE);
    //printf("read: the content is %s\n",buf);
    i = 0;
    while (i < bSIZE) {
        if (buf[i++] != (char)exp) {
            printf("WRONG %s offset %d should %x but %x\n",buf,foff,exp,buf[i-1]);
            close(fd);
            exit(1);
        }
    }
    close(fd);
    free(buf);
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
    int *mark;
    int *mexp;
    int exp;
    int j=0;

    printf("test file: %s\n",FILENAME);
    fsize = atoi(argv[1]);
    printf("fsize: %d\n", fsize);

    srand((unsigned)time(NULL));
    //MB
    pages = fsize * 1024 * 1024 / 4096;
    printf("file pages: %d\n", pages);
    mark = (int *)malloc(pages * sizeof(int));
    mexp = (int *)malloc(pages * sizeof(int));

    while(1) {
        for(i=0;i<pages;++i) {
            index = rand() % pages;
            exp = rand() % 256;
            mark[index] = 1;
            mexp[index] = exp;
            ww(index, exp);
            //printf("w %x %x\n",index ,(unsigned int)exp);
        }
        for(i=0;i<pages;++i) {
            index = rand() % pages;
            if (mark[index] == 1) {
                //printf("r %x %x\n",index , mexp[index]);
                rr(index, mexp[index]);
            } else {
                //printf("skip %d\n",i);
            }
        }
        printf("==============>  round %d ok\n",j);
        ++j;
        remove(path);
        memset(mark, 0 ,pages * sizeof(int));
        memset(mexp, 0 ,pages * sizeof(int));
    }
}
