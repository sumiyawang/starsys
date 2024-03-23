#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/hrtimer.h>
#include <linux/ktime.h>
#include <linux/smp.h>
#include <linux/interrupt.h>
#include <linux/sched.h>

#define INTERVAL_MS 20
#define INTERVAL_SEC 0
#define TARGET_CPU 164

#define cpu_rq(cpu)             (&per_cpu(runqueues, (cpu)))

static struct hrtimer hr_timer;

static void func_call(void *info) {
    int cpu = smp_processor_id();
    struct rq *rq = cpu_rq(cpu);
    resched_curr(rq);
}

static enum hrtimer_restart timer_callback(struct hrtimer *timer) {
    ktime_t now = hrtimer_cb_get_time(timer);
    ktime_t interval = ktime_set(INTERVAL_SEC, INTERVAL_MS * 1000000);

    // Trigger func_call on CPU 164
    smp_call_function_single(TARGET_CPU, func_call, NULL, 0);

    // Restart the timer
    hrtimer_forward(timer, now, interval);
    return HRTIMER_RESTART;
}

static int __init timer_init(void) {
    pr_info("timer_init\n");
    ktime_t interval = ktime_set(INTERVAL_SEC, 0);

    // Initialize and start the timer
    hrtimer_init(&hr_timer, CLOCK_MONOTONIC, HRTIMER_MODE_REL);
    hr_timer.function = &timer_callback;
    hrtimer_start(&hr_timer, interval, HRTIMER_MODE_REL);

    return 0;
}

static void __exit timer_exit(void) {
    // Cancel the timer
    hrtimer_cancel(&hr_timer);
}

module_init(timer_init);
module_exit(timer_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Your Name");
MODULE_DESCRIPTION("A hrtimer module that triggers func_call every 5 seconds on CPU 164.");
