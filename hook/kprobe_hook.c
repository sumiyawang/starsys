#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/kprobes.h>
#include <asm/uaccess.h>
#include <linux/kallsyms.h>
#include <linux/delay.h>
#include <asm-generic/current.h>
#include <linux/sched.h>
#include <scsi/scsi_host.h>
#include <scsi/scsi.h>
#include <scsi/scsi_device.h>
#include <scsi/scsi_transport_iscsi.h>

#define MAX_SYMBOL_LEN    64

static char symbol[MAX_SYMBOL_LEN] = "release_sock";
module_param_string(symbol, symbol, sizeof(symbol), 0644);
static struct kprobe kp = {
    .symbol_name    = symbol,
};

static int cur_c = 0;

u64 deepfunc(void)
{
    int size = 100;
    int stack_array[size];
    int i;
    int sum = 0;

    for (i = 0; i < size; ++i) {
        stack_array[i] = i;
    }

    for (i = 0; i < size; ++i) {
        sum += stack_array[i];
    }

    for (i = 0; i < size; ++i) {
        stack_array[i] = 0;
    }
    return sum;
}

static int std_delay(void)
{
    u64 start_time, end_time, elapsed_time;
    int i;
    u64 sum;
    u64 **p_addr;
    int x;
    int cpu = smp_processor_id();

    x = 0;

    start_time = ktime_get_ns();

    for (i = 0; i < 10; ++i) {
        x = x + deepfunc();
    }

    end_time = ktime_get_ns();

    elapsed_time = end_time - start_time;
    printk(KERN_INFO "CPU %d Loop completed. Elapsed time: %llu ns val %llx\n",cpu, elapsed_time, x);

    return 0;
}

static atomic_t fflag = ATOMIC_INIT(0);

//static int hook_iscsi_sw_tcp_pdu_xmit(struct iscsi_task *task)
//ssize_t hook_vfs_write(struct file *file, const char __user *buf, size_t count, loff_t *pos)
static int pre_handler(struct kprobe *p, struct pt_regs *regs)
{
    int cpu = smp_processor_id();
        if (atomic_cmpxchg(&fflag, 0, 1) == 0) {
            if (cur_c < 40) {
                ++cur_c;
                std_delay();
                //dump_stack();
            }
            atomic_set(&fflag, 0);
        }

    return 0;
}

static void post_handler(struct kprobe *p, struct pt_regs *regs,
                unsigned long flags)
{
}

static int __init kprobe_init(void)
{
    kp.pre_handler = pre_handler;
    kp.post_handler = post_handler;
    register_kprobe(&kp);
    return 0;
}

void __exit kprobe_exit(void)
{
    unregister_kprobe(&kp);
    pr_info("kp removed\n");
}

module_init(kprobe_init)
module_exit(kprobe_exit)
MODULE_LICENSE("GPL");
