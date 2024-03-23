#include <stdio.h>
#include <sys/mman.h>
#include <stdlib.h>
#include <sys/types.h>
#include <unistd.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdint.h>
#include <sys/prctl.h>

#define eout(msg) do { printf(msg); exit(1);} while (0)

void mem_addr(unsigned long vaddr, unsigned long *paddr)
{
    int pageSize = getpagesize();

    unsigned long v_pageIndex = vaddr / pageSize;
    unsigned long v_offset = v_pageIndex * sizeof(uint64_t);
    unsigned long page_offset = vaddr % pageSize;
    uint64_t item = 0;

    int fd = open("/proc/self/pagemap", O_RDONLY);
    if(fd == -1)
    {
        printf("open /proc/self/pagemap error\n");
        return;
    }

    if(lseek(fd, v_offset, SEEK_SET) == -1)
    {
        printf("sleek error\n");
        return; 
    }

    if(read(fd, &item, sizeof(uint64_t)) != sizeof(uint64_t))
    {
        printf("read item error\n");
        return;
    }

    if((((uint64_t)1 << 63) & item) == 0)
    {
        printf("page present is 0");
        return ;
    }

    uint64_t phy_pageIndex = (((uint64_t)1 << 55) - 1) & item;

    *paddr = (phy_pageIndex * pageSize) + page_offset;
}

const int a = 100;

int main()
{
    int b = 100;
    static c = 100;
    const int d = 100;
    char *str = "Hello World!";

    unsigned long phy = 0;
    int fd;
    char *p;
    static int k = 0;
    //fd = open("/dev/hugepages2M/11", O_CREAT | O_RDWR);
    //if (fd == -1)
    //    eout("open error\n");

    //p = mmap(NULL, 2*1024*1024, PROT_READ|PROT_WRITE, MAP_SHARED, -1, 0);
    //prctl(PR_MCE_KILL, PR_MCE_KILL_SET, PR_MCE_KILL_EARLY, 0, 0);
    p = mmap(NULL, 2*1024*1024, PROT_READ|PROT_WRITE, MAP_ANONYMOUS|MAP_PRIVATE|MAP_HUGETLB, -1, 0);
    if (p == MAP_FAILED) {
        eout("MAP_FAILED\n");
    } 
    p[0] = '1';
    mem_addr((unsigned long)&p, &phy);
    printf("ori pid = %d, virtual addr = %p , physical addr = %lx \n", getpid(), &p, phy);
    

    int pid = fork();
    if(pid == 0)
    {
        while(1) {
            //p[0] = '1';
            //mem_addr((unsigned long)&p, &phy);
            printf("son pid = %d, virtual addr = %p , physical addr = %lx\n", getpid(), &p, phy);
            sleep(5);
            //exit(0);
        }
    }
    else
    { 
        while(1) {
            ++k;
            phy = 0;
            //if (k < 3)
            mem_addr((unsigned long)&p, &phy);
            printf("ori pid = %d, virtual addr = %p , physical addr = %lx p[0]=%c\n", getpid(), &p, phy, p[0]);
            //printf("ori pid = %d, virtual addr = %p , physical addr = %lx \n", getpid(), &p, phy);
            sleep(5);
        }
    }

    sleep(10000);
    free(p);
    waitpid();
    return 0;
}
