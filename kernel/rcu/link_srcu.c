#include <linux/module.h>
#include <linux/kthread.h>
#include <linux/delay.h>
#include <linux/slab.h>

#define TR 4
#define TW 2
#define TS 2

struct task_struct *t_r[TR];
struct task_struct *t_w[TW];
struct task_struct *t_s[TS];

//struct task_struct *t_s3;
//struct task_struct *t_s4;

struct comms
{
        int a1;
        int a2;
        int a3;
	struct list_head list;
};

static struct srcu_struct srcup;
static struct comms *p_scomm = NULL;
static DEFINE_RAW_SPINLOCK(comms_lock);
static int base = 1;

LIST_HEAD(srcu_lk);

static int rcu_reader(void *data)
{
        struct comms *p = NULL;
        int x,y,z;
        int idx;
	u64 pc = 0;
        pr_info("rcu reader start, pid %d\n", current->pid);
        while (!kthread_should_stop()) {
                idx = srcu_read_lock(&srcup);
		list_for_each_entry_rcu(p, &srcu_lk, list) {
			msleep(100);
                	pr_info("%s rcu read p:%lx %x %x %x %lx\n",current->comm, p, p->a1, p->a2, p->a3, pc);
		}
                srcu_read_unlock(&srcup, idx);
		++pc;

                cond_resched();
        }
        pr_info("rcu reader stop, pid %d %x %x %x %lx\n", current->pid, x, y, z, pc);
        return 0;
}

static int rcu_writer(void *data)
{
        struct comms *newc;
        struct comms *oldp;
	char *cmd = current->comm;

        pr_info("rcu writer start, pid %d\n", current->pid);
        while (!kthread_should_stop()) {
                newc = (struct comms*)kzalloc(sizeof(struct comms), GFP_KERNEL);
		raw_spin_lock(&comms_lock);
		oldp = list_first_or_null_rcu(&srcu_lk, struct comms, list);
		*newc = *oldp;

                newc->a1 = base + 1;
                newc->a2 = base + 1;
                newc->a3 = base + 1;
                ++base;
		list_replace_rcu(&oldp->list, &newc->list);
		raw_spin_unlock(&comms_lock);
                synchronize_srcu(&srcup);
                kfree(oldp);
                cond_resched();
        }
        pr_info("rcu writer stop, pid %d\n", current->pid);

        return 0;
}

static int rcu_sync(void *data)
{
        pr_info("rcu sync start, pid %d\n", current->pid);
        while (!kthread_should_stop()) {
                synchronize_srcu(&srcup);
                cond_resched();
                msleep(1);
        }
        pr_info("rcu sync stop, pid %d\n", current->pid);

        return 0;
}

static int __init rcu_start(void)
{
        pr_info("rcu_start");
        p_scomm = (struct comms *)kzalloc(sizeof(struct comms), GFP_KERNEL);
        init_srcu_struct(&srcup);
	
	int i = 1;
	list_add_rcu(&p_scomm->list, &srcu_lk);

	for(i = 1; i <= TR; ++i) {
		t_r[i-1] = kthread_run(rcu_reader, NULL, "rcu_r");
	}

	for(i = 1; i <= TW; ++i) {
        	t_w[i-1] = kthread_run(rcu_writer, NULL, "rcu_w");
	}

	for(i = 1; i <= TS; ++i) {
        	t_s[i-1] = kthread_run(rcu_sync, NULL, "rcu_s");
	}

        return 0;
}

static void rcu_stop(void)
{
	int i = 1;
	for(i = 1; i <= TS; ++i) {
		kthread_stop(t_s[i-1]);
	}
	for(i = 1; i <= TR; ++i) {
		kthread_stop(t_r[i-1]);
	}
	for(i = 1; i <= TW; ++i) {
		kthread_stop(t_w[i-1]);
	}
}

module_init(rcu_start);
module_exit(rcu_stop);
MODULE_LICENSE("GPL");

