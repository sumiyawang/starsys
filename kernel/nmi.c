#include <linux/module.h>
#include <linux/perf_event.h>
#include <linux/nmi.h>

static DEFINE_PER_CPU(struct perf_event *, nmi_ev);

static struct perf_event_attr wd_hw_attr = {                                                          
        .type           = PERF_TYPE_HARDWARE,                                                         
        .config         = PERF_COUNT_HW_CPU_CYCLES,                                                   
        .size           = sizeof(struct perf_event_attr),                                             
        .pinned         = 1,                                                                          
        .disabled       = 0,                                                                          
};

spinlock_t spstack;

static void nmi_callback(struct perf_event *event,
                                       struct perf_sample_data *data,
                                       struct pt_regs *regs)
{
    spin_lock(&spstack);
    pr_info("+++NMI+++\n");
    dump_stack();
    spin_unlock(&spstack);
}

u64 hw_nmi_get_sample_period(int watchdog_thresh)
{
    return (u64)(cpu_khz) * 1000 * watchdog_thresh;
}

static int __init percpu_nmi_stack_on(int cpu)
{
    struct perf_event_attr *wd_attr;
    struct perf_event *evt;

    wd_attr = &wd_hw_attr;
    wd_attr->sample_period = hw_nmi_get_sample_period(5);
    evt = perf_event_create_kernel_counter(wd_attr, cpu, NULL, nmi_callback, NULL);
    if (IS_ERR(evt)) {
        pr_info("Perf event create on CPU %d failed with %ld\n", cpu,
                 PTR_ERR(evt));
        return PTR_ERR(evt);
    }
    this_cpu_write(nmi_ev, evt);
    pr_info("CPU %d nmi add\n", cpu);
    perf_event_enable(this_cpu_read(nmi_ev));
    return 0;
}

static int __init nmi_stack_on(void)
{
    int cpu;
    spin_lock_init(&spstack);
//    for_each_online_cpu(cpu) {
//        percpu_nmi_stack_on(cpu);
//    }
    percpu_nmi_stack_on(164);
    return 0;
}

nmi_stack_off(void)
{
    int cpu;
    for_each_online_cpu(cpu) {
        struct perf_event *event = per_cpu(nmi_ev, cpu);
        if (event) {
            perf_event_disable(event);
            pr_info("CPU %d nmi_stack_off \n", cpu);
        }
    }
}

module_init(nmi_stack_on);
module_exit(nmi_stack_off);

MODULE_LICENSE("GPL");
