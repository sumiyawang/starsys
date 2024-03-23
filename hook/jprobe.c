#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/kprobes.h>
#include <asm/uaccess.h>
#include <linux/kallsyms.h>
#include <linux/delay.h>
#include <asm-generic/current.h>
#include <linux/sched.h>

#define NUM 6

/*
* hook these functions:
* struct machine_ops machine_ops = { 
*         .power_off = native_machine_power_off,
*         .shutdown = native_machine_shutdown,
*         .emergency_restart = native_machine_emergency_restart,
*         .restart = native_machine_restart,
*         .halt = native_machine_halt,
* #ifdef CONFIG_KEXEC_CORE
*         .crash_shutdown = native_machine_crash_shutdown,
* #endif
* };
*/

MODULE_INFO(vermagic, "4.4.0-130-generic SMP mod_unload modversions retpoline ");

static struct jprobe my_jprobe[NUM];

static void print_comm(char *comm)
{
    char cp_comm[TASK_COMM_LEN];
    strncpy(cp_comm, comm, TASK_COMM_LEN);
    cp_comm[TASK_COMM_LEN-1] = '\0';
    pr_emerg("%s \n", comm);
}

static int dump_call_stack(void){
    int count = 0;
    struct task_struct *pp;
    if (IS_ERR_OR_NULL(current)){
        return 0;
    }
    pp = current->real_parent;
    while (!IS_ERR_OR_NULL(pp) && pp != &init_task) {
        print_comm(pp->comm);
        pp = pp->real_parent;
        count++;
        if (count == 10) {
            break;
        }
    }
    return 0;
}



void dump_log(void)
{
    pr_emerg("User space call:\n");
    dump_call_stack();
    pr_emerg("Kernel stack:\n");
    dump_stack();
}

static void hook_native_machine_emergency_restart(void)
{
    dump_log();

    jprobe_return();
    return ;
}

static void hook_native_machine_power_off(void)
{
    dump_log();

    jprobe_return();
    return ;
}

static void hook_native_machine_shutdown(void)
{
    dump_log();

    jprobe_return();
    return ;
}

static void hook_native_machine_restart(char *__unused)
{
    dump_log();

    jprobe_return();
    return ;
}

static void hook_native_machine_halt(void)
{
    dump_log();

    jprobe_return();
    return ;
}

void hook_native_machine_crash_shutdown(struct pt_regs *regs)
{
    dump_log();

    jprobe_return();
    return ;
}

static int __init jprobe_init(void)
{
    int ret;
    int i,j;
    my_jprobe[0].entry = hook_native_machine_emergency_restart;
    my_jprobe[0].kp.symbol_name = "native_machine_emergency_restart";
    my_jprobe[1].entry = hook_native_machine_power_off;
    my_jprobe[1].kp.symbol_name = "native_machine_power_off";
    my_jprobe[2].entry = hook_native_machine_shutdown;
    my_jprobe[2].kp.symbol_name = "native_machine_shutdown";
    my_jprobe[3].entry = hook_native_machine_restart;
    my_jprobe[3].kp.symbol_name = "native_machine_restart";
    my_jprobe[4].entry = hook_native_machine_halt;
    my_jprobe[4].kp.symbol_name = "native_machine_halt";
    my_jprobe[5].entry = hook_native_machine_crash_shutdown;
    my_jprobe[5].kp.symbol_name = "native_machine_crash_shutdown";
    
    for (i = 0; i < NUM; ++i)
    {
        ret = register_jprobe(&(my_jprobe[i]));
        if (ret < 0) {
            printk(KERN_INFO "register_jprobe failed, returned %d\n", ret);
            for (j = i-1; j >= 0; --j)
            {
                unregister_jprobe(&(my_jprobe[j]));
                printk(KERN_INFO "jprobe at %p unregistered\n", my_jprobe[j].kp.addr);
            }
            return -1;
        }
        printk(KERN_INFO "Planted jprobe at %p, handler addr %p\n",
               my_jprobe[i].kp.addr, my_jprobe[i].entry);
    }

    return 0;
}



static void __exit jprobe_exit(void)
{
    int i;
    for (i = 0; i < NUM; ++i)
    {
        unregister_jprobe(&(my_jprobe[i]));
        printk(KERN_INFO "jprobe at %p unregistered\n", my_jprobe[i].kp.addr);
    }
}

module_init(jprobe_init)
module_exit(jprobe_exit)
MODULE_LICENSE("GPL");
