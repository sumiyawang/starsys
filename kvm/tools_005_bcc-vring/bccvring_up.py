#!/usr/bin/python

from __future__ import print_function
from bcc import BPF
import time
from datetime import datetime
from time import sleep
import os
import sys, getopt

#BPF
b = BPF(text="""

#include <linux/virtio_ring.h>
#include <linux/kobject.h>

struct data_t {
    u64 ts;
    u32 pid;
    u8 type;
    u32 data1;
    u32 data2;
    char name[32];
};

struct virtqueue {
        struct list_head list;
        void (*callback)(struct virtqueue *vq);
        const char *name;
        struct virtio_device *vdev;
        unsigned int index;
        unsigned int num_free;
        void *priv;
};

struct vring_virtqueue {
        struct virtqueue vq;

        /* Actual memory layout for this queue */
        struct vring vring;

        /* Can we use weak barriers? */
        bool weak_barriers;

        /* Other side has made a mess, don't try any more. */
        bool broken;

        /* Host supports indirect buffers */
        bool indirect;

        /* Host publishes avail event idx */
        bool event;

        /* Head of free buffer list. */
        unsigned int free_head;
        /* Number we've added since last sync. */
        unsigned int num_added;

        /* Last used index we've seen. */
        u16 last_used_idx;

        /* Last written value to avail->flags */
        u16 avail_flags_shadow;

        /* Last written value to avail->idx in guest byte order */
        u16 avail_idx_shadow;
};


BPF_PERF_OUTPUT(events);
BPF_HISTOGRAM(distsd);
BPF_HISTOGRAM(distrc);
BPF_HISTOGRAM(moreputsq);
BPF_HASH(distmax, u32, u64);  //key: irq number  value: virtn
BPF_HASH(putmax, u32, u64);  //key: irq number  value: virtn
BPF_HASH(kickcount, u32, u64);  //key: irq number  value: virtn
BPF_HASH(minfreesq, u32, u64);  //key: irq number  value: virtn
BPF_HASH(minfreerq, u32, u64);  //key: irq number  value: virtn

int kprobe__virtqueue_add_outbuf(struct pt_regs *ctx, struct virtqueue *vq) {
    struct data_t data = {};
    struct vring_virtqueue *vvq = (struct vring_virtqueue *)vq;
    
    int a = vvq->vring.used->idx;
    int b = vvq->last_used_idx; 
    int more = a - b;
    if (more < 0) 
        more = a + (65536 - b);
    distsd.increment(bpf_log2l(more));

    u32 mfree = vvq->vq.num_free;
    u32 key = 0;
    u64 *value = minfreesq.lookup(&key);
    
    if (value == NULL) {
        u64 val = mfree;
        minfreesq.update(&key, &val);
        return 0;
    }

    if (*value > mfree) {
        u64 val = mfree;
        minfreesq.update(&key, &val);
    }
    a = vvq->vring.avail->idx;
    b = vvq->vring.used->idx;
    int moreput = a - b;

    if (moreput < 0) {
        moreput = a + (65536 - b);
        //debug the boundary data
        //data.data1 = a;
        //data.data2 = b;
        //events.perf_submit(ctx, &data, sizeof(data));
    }
    moreputsq.increment(bpf_log2l(moreput));

    u64 *value1 = putmax.lookup(&key);

    if (value1 == NULL) {
        u64 val1 = moreput;
        putmax.update(&key, &val1);
        return 0;
    }

    if (*value1 < moreput) {
        u64 val1 = moreput;
        putmax.update(&key, &val1);
    }

    return 0;
};

int kprobe__virtqueue_kick(void *ctx) {
    u32 key = 0;
    u64 *value = kickcount.lookup(&key);
    if (value == NULL) {
        u64 val = 1;
        kickcount.update(&key, &val);
    } else {
        u64 val = *value + 1;
        kickcount.update(&key, &val);
    }
    return 0;
}

int kprobe__virtqueue_add_inbuf_ctx(struct pt_regs *ctx, struct virtqueue *vq) {
    struct data_t data = {};
    struct vring_virtqueue *vvq = (struct vring_virtqueue *)vq;
    int a = vvq->vring.used->idx;
    int b = vvq->last_used_idx;
    int more = a - b;
    if (more < 0) 
        more = a + (65536 - b);

    distrc.increment(bpf_log2l(more));
    u32 key = 0;
    u64 *value = distmax.lookup(&key);

    if (value == NULL) {
        u64 val = more;
        distmax.update(&key, &val);
        return 0;
    }

    if (*value < more) {
        u64 val = more;
        distmax.update(&key, &val);
    }

    u32 mfree = vvq->vq.num_free;

    u64 *value1 = minfreerq.lookup(&key);
    
    if (value1 == NULL) {
        u64 val1 = mfree;
        minfreerq.update(&key, &val1);
        return 0;
    }

    if (*value1 > mfree) {
        u64 val1 = mfree;
        minfreerq.update(&key, &val1);
    }

    return 0;
};

""")

#this for event debug
#def print_event(cpu, data, size):
#    event = b["events"].event(data) 
#    print("availd: %d  used: %d" % (event.data1, event.data2))

stime=300
try:
    opts, args = getopt.getopt(sys.argv[1:],"s:")
except getopt.GetoptError:
    exit()
for opt, arg in opts:
    if opt == '-s':
        stime = int(arg)
    elif opt in ("-h"):
        print("-s time")

print("start tracing...")
#b["events"].open_perf_buffer(print_event)
#while 1:
#    try:
#        b.perf_buffer_poll()
#    except KeyboardInterrupt:
#        func()
#        exit()

try:
    sleep(stime)
except KeyboardInterrupt:
    print("")

print("Note: vring distance = used->idx - last_used_idx, bigger means worse")
print("recv-Q consume pkg cap: (used->idx - last_used_idx)")
print("")
b["distrc"].print_log2_hist("recv-Q distance")
counts = b["distmax"]
if counts :
    tab = counts.items()
    print("max: %d " % int(tab[0][1].value))
print("")

print("send-Q send pkg cap: (avaid->idx - used->idx)")
b["moreputsq"].print_log2_hist("send-Q put more")
counts = b["putmax"]
if counts :
    tab = counts.items()
    print("max: %d " % int(tab[0][1].value))
print("")

print("send-Q free pkg cap: (used->idx - last_used_idx)")
b["distsd"].print_log2_hist("send-Q distance")
print("")


counts = b["kickcount"]
if counts :
    tab = counts.items()
    print("virtqueue_kick total: %d " % int(tab[0][1].value))

counts = b["minfreesq"]
if counts :
    tab = counts.items()
    print("min numfree in send-Q: %d " % int(tab[0][1].value))

counts = b["minfreerq"]
if counts :
    tab = counts.items()
    print("min numfree in recv-Q: %d " % int(tab[0][1].value))
