#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/ktime.h>
#include <linux/sched.h>
#include <asm/tlbflush.h>
#include <linux/mm.h>
#include <linux/cpu.h>
#include <linux/delay.h>

#include <linux/idr.h>

#include <linux/kallsyms.h>

#include <linux/hashtable.h>

#include <linux/kthread.h>

#include <linux/slab.h>

#define MAX_LOOP 100



#define assert_rcu_or_pool_mutex()                                      \
        rcu_lockdep_assert(rcu_read_lock_sched_held() ||                \
                           lockdep_is_held(&wq_pool_mutex),             \
                           "sched RCU or wq_pool_mutex should be held")

#define for_each_pool(pool, pi)                                         \
        idr_for_each_entry(p_worker_pool_idr, pool, pi)                  \
                if (({ assert_rcu_or_pool_mutex(); false; })) { }       \
                else

#define for_each_pool_worker(worker, wi, pool)                          \
        idr_for_each_entry(&(pool)->worker_idr, (worker), (wi))         \
                if (({ assert_manager_or_pool_lock((pool)); false; })) { } \
                else

#ifdef CONFIG_LOCKDEP
#define assert_manager_or_pool_lock(pool)                               \
        WARN_ONCE(debug_locks &&                                        \
                  !lockdep_is_held(&(pool)->manager_mutex) &&           \
                  !lockdep_is_held(&(pool)->lock),                      \
                  "pool->manager_mutex or ->lock should be held")
#else           
#define assert_manager_or_pool_lock(pool)       do { } while (0)
#endif

enum {
        POOL_MANAGE_WORKERS     = 1 << 0,       /* need to manage workers */
        POOL_DISASSOCIATED      = 1 << 2,       /* cpu can't serve workers */
        POOL_FREEZING           = 1 << 3,       /* freeze in progress */

        /* worker flags */
        WORKER_STARTED          = 1 << 0,       /* started */
        WORKER_DIE              = 1 << 1,       /* die die die */
        WORKER_IDLE             = 1 << 2,       /* is idle */
        WORKER_PREP             = 1 << 3,       /* preparing to run works */
        WORKER_CPU_INTENSIVE    = 1 << 6,       /* cpu intensive */
        WORKER_UNBOUND          = 1 << 7,       /* worker is unbound */
        WORKER_REBOUND          = 1 << 8,       /* worker was rebound */

        WORKER_NOT_RUNNING      = WORKER_PREP | WORKER_CPU_INTENSIVE |
                                  WORKER_UNBOUND | WORKER_REBOUND,

        NR_STD_WORKER_POOLS     = 2,            /* # standard pools per cpu */

        UNBOUND_POOL_HASH_ORDER = 6,            /* hashed by pool->attrs */
        BUSY_WORKER_HASH_ORDER  = 6,            /* 64 pointers */

        MAX_IDLE_WORKERS_RATIO  = 4,            /* 1/4 of busy can be idle */
        IDLE_WORKER_TIMEOUT     = 300 * HZ,     /* keep idle ones for 5 mins */

        MAYDAY_INITIAL_TIMEOUT  = HZ / 100 >= 2 ? HZ / 100 : 2,
                                                /* call for help after 10ms
                                                   (min two ticks) */
        MAYDAY_INTERVAL         = HZ / 10,      /* and then every 100ms */
        CREATE_COOLDOWN         = HZ,           /* time to breath after fail */

        /*
         * Rescue workers are used only on emergencies and shared by
         * all cpus.  Give -20.
         */
        RESCUER_NICE_LEVEL      = -20,
        HIGHPRI_NICE_LEVEL      = -20,

        WQ_NAME_LEN             = 24,
};


unsigned int pid;
module_param(pid, uint, S_IRUSR|S_IWUSR);

// sym
struct module_symbol {
    struct module * mod; //input
    const char * symstr; //input
    unsigned long symaddr; //output. initialized 0
};

int kallsyms_search_cb(void * param, const char * symstr, struct module * mod,
                              unsigned long address)
{
    struct module_symbol * pms = (typeof(pms))param;
    if (mod != pms->mod)
        return 0;

    if (strcmp(symstr, pms->symstr) == 0) {
        pms->symaddr = address;
        return 1;
    }

    return 0;
}

// find sym
struct mutex * p_wq_pool_mutex;
struct idr * p_worker_pool_idr;


//pool struct
struct worker_pool {
        spinlock_t              lock;           /* the pool lock */
        int                     cpu;            /* I: the associated cpu */
        int                     node;           /* I: the associated node ID */
        int                     id;             /* I: pool ID */
        unsigned int            flags;          /* X: flags */
                        
        unsigned long           watchdog_ts;    /* L: watchdog timestamp */
                
        struct list_head        worklist;       /* L: list of pending works */
        int                     nr_workers;     /* L: total number of workers */
        
        /* nr_idle includes the ones off idle_list for rebinding */
        int                     nr_idle;        /* L: currently idle ones */

        struct list_head        idle_list;      /* X: list of idle workers */
        struct timer_list       idle_timer;     /* L: worker idle timeout */
        struct timer_list       mayday_timer;   /* L: SOS timer for workers */
                        
        /* a workers is either on busy_hash or idle_list, or the manager */
        DECLARE_HASHTABLE(busy_hash, BUSY_WORKER_HASH_ORDER);
                                                /* L: hash of busy workers */

        /* see manage_workers() for details on the two manager mutexes */
        struct mutex            manager_arb;    /* manager arbitration */
        struct mutex            manager_mutex;  /* manager exclusion */
        struct idr              worker_idr;     /* MG: worker IDs and iteration */

        struct workqueue_attrs  *attrs;         /* I: worker attributes */
        struct hlist_node       hash_node;      /* PL: unbound_pool_hash node */
        int                     refcnt;         /* PL: refcnt for unbound pools */

        /*
         * The current concurrency level.  As it's likely to be accessed
         * from other CPUs during try_to_wake_up(), put it in a separate
         * cacheline.
         */
        atomic_t                nr_running ____cacheline_aligned_in_smp;

        /*
         * Destruction of pool is sched-RCU protected to allow dereferences
         * from get_work_pool().
         */
        struct rcu_head         rcu;
} ____cacheline_aligned_in_smp;

struct worker {
        /* on idle list while idle, on busy hash table while busy */
        union {
                struct list_head        entry;  /* L: while idle */
                struct hlist_node       hentry; /* L: while busy */
        };  

        struct work_struct      *current_work;  /* L: work being processed */
        work_func_t             current_func;   /* L: current_work's fn */
        struct pool_workqueue   *current_pwq; /* L: current_work's pwq */
        bool                    desc_valid;     /* ->desc is valid */
        struct list_head        scheduled;      /* L: scheduled works */

        /* 64 bytes boundary on 64bit, 32 on 32bit */

        struct task_struct      *task;          /* I: worker task */
        struct worker_pool      *pool;          /* I: the associated pool */
                                                /* L: for rescuers */

        unsigned long           last_active;    /* L: last active timestamp */
        unsigned int            flags;          /* X: flags */
        int                     id;             /* I: worker id */

        /*  
         * Opaque string set with work_set_desc().  Printed out with task
         * dump for debugging - WARN, BUG, panic or sysrq.
         */
        char                    desc[WORKER_DESC_LEN];

        /* used only by rescuers to point to the target workqueue */
        struct workqueue_struct *rescue_wq;     /* I: the workqueue to rescue */
};



void * relocate_symbol(char * module_name, char * symbol_name)
{
        struct module_symbol ms = {};
        if (module_name) {
                ms.mod = find_module(module_name);
                if (!ms.mod) {
                        printk(KERN_ERR "not found symbol %s\n", module_name);
                        return NULL;
                }

                if (0 != ref_module(THIS_MODULE, ms.mod)) {
                        printk(KERN_ERR "can't ref module %s\n", module_name);
                        return NULL;
                }
        }

        ms.symstr = symbol_name;
        ms.symaddr = 0;

        kallsyms_on_each_symbol(kallsyms_search_cb, &ms);
        if (unlikely(!ms.symaddr)) {
                printk(KERN_ERR "can't find symbol %s\n", symbol_name);
                return NULL;
        }
        printk(KERN_INFO "found symbol %s at 0x%lx\n", symbol_name, (unsigned long )ms.symaddr);
        return (void *)ms.symaddr;
}

/**
 * destroy_worker - destroy a workqueue worker                                                                        
 * @worker: worker to be destroyed                                                                                    
 *
 * Destroy @worker and adjust @pool stats accordingly.                                                                
 *
 * CONTEXT:
 * spin_lock_irq(pool->lock) which is released and regrabbed.                                                         
 */
static void destroy_worker(struct worker *worker)                                                                     
{       
        struct worker_pool *pool = worker->pool;                                                                      
        
        lockdep_assert_held(&pool->manager_mutex);                                                                    
        lockdep_assert_held(&pool->lock);                                                                             
        
        /* sanity check frenzy */
        if (WARN_ON(worker->current_work) ||
            WARN_ON(!list_empty(&worker->scheduled)))                                                                 
                return;                                                                                               
        
        if (worker->flags & WORKER_STARTED)                                                                           
                pool->nr_workers--;
        if (worker->flags & WORKER_IDLE)                                                                              
                pool->nr_idle--;                                                                                      
        
        /*
         * Once WORKER_DIE is set, the kworker may destroy itself at any
         * point.  Pin to ensure the task stays until we're done with it.
         */
        get_task_struct(worker->task);

        list_del_init(&worker->entry);
        worker->flags |= WORKER_DIE;

        idr_remove(&pool->worker_idr, worker->id);

        spin_unlock_irq(&pool->lock);

        kthread_stop(worker->task);
        put_task_struct(worker->task);
        kfree(worker);

        spin_lock_irq(&pool->lock);
}

bool woker_idle(struct worker *kw, struct worker_pool *pool)
{
	struct worker *it_worker;
	if (kw->current_work || !list_empty(&kw->scheduled))
		return false;

	list_for_each_entry(it_worker, &pool->idle_list, entry) {
		if (it_worker == kw)
			return true;
	}
	return false;
}

static int killkw(void)
{
        int wait = 1;
        int waitidle = 1;
	int pi;
	int wi;
	struct task_struct *wtsk;
	struct worker_pool *pool;
	struct worker *worker;
	struct worker *kw = NULL;

	p_wq_pool_mutex = relocate_symbol(NULL, "wq_pool_mutex");
	p_worker_pool_idr = relocate_symbol(NULL, "worker_pool_idr");
	pr_info("arg pid: %d\n",pid);

	mutex_lock(p_wq_pool_mutex);

	pr_info("try get wq_pool_mutex %d times\n", wait);

	for_each_pool(pool, pi) {
		spin_lock_irq(&pool->lock);
		mutex_lock(&pool->manager_arb);
		mutex_lock(&pool->manager_mutex);
		pr_info("in pool: 0x%lx\n",(unsigned long)pool);
		for_each_pool_worker(worker, wi, pool) {
			wtsk = worker->task;
			pr_info("  ->kworker: %s %d\n",wtsk->comm, wtsk->pid);
			if (pid) {
				if (pid == wtsk->pid) {
					kw = worker;
					goto found;
				}
			}
		}
found:
		if (kw) {
			mutex_unlock(p_wq_pool_mutex);
			pr_info("found kworker 0x%lx\n",(unsigned long)kw);
			while (1) {
				if (!woker_idle(kw, pool)) {
					mutex_unlock(&pool->manager_mutex);
					mutex_unlock(&pool->manager_arb);
					spin_unlock_irq(&pool->lock);
					++waitidle;
					pr_info("waitidle %d\n", waitidle);
					if (waitidle > MAX_LOOP) {
						pr_info("worker not idle always\n");
						return 0;
					}
					msleep(1);
					spin_lock_irq(&pool->lock);
					mutex_lock(&pool->manager_arb);
					mutex_lock(&pool->manager_mutex);
				} else {
					//do kworker event
					pr_info("kill and create new kworker\n");
					destroy_worker(kw);
					pr_info("kill finish\n");
					mutex_unlock(&pool->manager_mutex);
					mutex_unlock(&pool->manager_arb);
					spin_unlock_irq(&pool->lock);
					return 0;
				}
			}
		}
		mutex_unlock(&pool->manager_mutex);
		mutex_unlock(&pool->manager_arb);
		spin_unlock_irq(&pool->lock);
	}

	mutex_unlock(p_wq_pool_mutex);
	return 0;
}

static void exit_killkw(void) {
}

module_init(killkw);
module_exit(exit_killkw);
MODULE_AUTHOR("Ruu");

MODULE_LICENSE("GPL");
