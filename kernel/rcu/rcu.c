#include <linux/module.h>
#include <linux/kthread.h>
#include <linux/delay.h>
#include <linux/slab.h>

struct task_struct *t_r;
struct task_struct *t_w;

struct comms
{
	int a1;
	int a2;
	int a3;
	struct rcu_head rcu;
};

static struct comms *p_scomm = NULL;

static int rcu_reader(void *data)
{
	struct comms *p = NULL;
	int x,y,z;
	pr_info("rcu reader start, pid %d\n", current->pid);
	while (!kthread_should_stop()) {
		rcu_read_lock();
		p = rcu_dereference(p_scomm);
		x = p->a1;
		//msleep(50);
		y = p->a2;
		z = p->a3;
		
		pr_info("rcu read p:%lx %x %x %x\n", p, p->a1, p->a2, p->a3);
		rcu_read_unlock();

		cond_resched();
		msleep(100);
	}
	return 0;
}

static void sfree(struct rcu_head *rh)
{
	struct comms *fp = container_of(rh, struct comms, rcu);
	kfree(fp);
	pr_info("kfree %lx\n", fp);
}

static int rcu_writer(void *data)
{
	struct comms *newc;
	struct comms *oldp;
	int base = 1;

	pr_info("rcu writer start, pid %d\n", current->pid);
	while (!kthread_should_stop()) {
		newc = (struct comms*)kzalloc(sizeof(struct comms), GFP_KERNEL);
		pr_info("kmalloc  %lx\n", newc);
		newc->a1 = base + 1;
		newc->a2 = base + 1;
		msleep(5);
		newc->a3 = base + 1;
		oldp = p_scomm;
		rcu_assign_pointer(p_scomm, newc);
//		call_rcu(&oldp->rcu, sfree);
		synchronize_rcu();
		kfree(oldp);
		pr_info("kfree  %lx\n", oldp);
		++base;
		cond_resched();
		msleep(100);
	}

	return 0;
}

static int __init rcu_start(void)
{
	pr_info("rcu_start");
	p_scomm = (struct comms *)kzalloc(sizeof(struct comms), GFP_KERNEL);
	t_r = kthread_run(rcu_reader, NULL, "rcu_r");
	t_w = kthread_run(rcu_writer, NULL, "rcu_w");
	return 0;
}

static void rcu_stop(void)
{
	kthread_stop(t_r);	
	kthread_stop(t_w);	
}

module_init(rcu_start);
module_exit(rcu_stop);
MODULE_LICENSE("GPL");

