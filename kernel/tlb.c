#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/ktime.h>
#include <linux/sched.h>
#include <asm/tlbflush.h>
#include <linux/mm.h>
#include <linux/cpu.h>

static void do_flush_tlb_all(void *info)
{
        __flush_tlb_global();
        pr_err("__flush_tlb_global done %d\n",smp_processor_id());
}
static int __init

init_flush_tlb(void) {

    pr_err("#############################################################\n");
    int i=0;
    /* Return error to avoid annoying rmmod. */
    for(i=1;i<100;++i) 
        on_each_cpu(do_flush_tlb_all, NULL, 0); 
    return 0;
}
exit_flush_tlb(void) {

    return 0;
}

module_init(init_flush_tlb);
module_exit(exit_flush_tlb);

MODULE_LICENSE("GPL");
