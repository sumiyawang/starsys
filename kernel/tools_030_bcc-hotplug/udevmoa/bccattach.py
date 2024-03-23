#!/usr/bin/python

from bcc import BPF
import time
from datetime import datetime
import ctypes as ct

#BPF
b = BPF(text="""
#include <linux/kobject.h>
struct data_t {
    u64 ts;
    u32 pid;
    u8 type;
    u8 uenv;
    u8 virtn;
    char name[32];
};
struct device_attribute {
        struct attribute        attr;
        ssize_t (*show)(struct device *dev, struct device_attribute *attr,
                        char *buf);
        ssize_t (*store)(struct device *dev, struct device_attribute *attr,
                         const char *buf, size_t count);
};


BPF_PERF_OUTPUT(events);
BPF_HASH(drvn, u32, u64);  //key: irq number  value: virtn


int kprobe__acpi_irq(void *ctx) {
    struct data_t data = {};
    data.pid= bpf_get_current_pid_tgid();
    data.ts = bpf_ktime_get_ns() / 1000;
    data.type = 0;

    u32 key = 0;
    u64 value = 0;
    drvn.update(&key, &value);

    events.perf_submit(ctx, &data, sizeof(data));
    return 0;
};

int kprobe__pci_scan_slot(void *ctx) {
    struct data_t data = {};
    data.pid= bpf_get_current_pid_tgid();
    data.ts = bpf_ktime_get_ns() / 1000;
    data.type = 1;

    u32 key = 0;
    u64 *value = drvn.lookup(&key);
    if (value == NULL)
        return 0;
    u64 val = *value + 1;
    drvn.update(&key, &val);
    
    events.perf_submit(ctx, &data, sizeof(data));
    return 0;
};

int kprobe__pci_device_add(void *ctx) {
    struct data_t data = {};
    data.pid= bpf_get_current_pid_tgid();
    data.ts = bpf_ktime_get_ns() / 1000;
    data.type = 2;
    
    u32 key = 0;
    u64 *value = drvn.lookup(&key);
    if (value == NULL)
        return 0;
    data.virtn = *value;
    
    events.perf_submit(ctx, &data, sizeof(data));
    return 0;
};

int kprobe__kobject_uevent_env(struct pt_regs *ctx, struct kobject *kobj, enum kobject_action action) {
    struct data_t data = {};
    data.pid= bpf_get_current_pid_tgid();
    data.ts = bpf_ktime_get_ns() / 1000;
    data.uenv = action;
    const char *tmp = kobj->name;
    bpf_probe_read(data.name,32,tmp);
    data.type = 3;

    events.perf_submit(ctx, &data, sizeof(data));
    return 0;
};

int kretprobe__virtblk_probe(struct pt_regs *ctx) {
    struct data_t data = {};
    data.uenv = PT_REGS_RC(ctx);
    data.pid= bpf_get_current_pid_tgid();
    data.ts = bpf_ktime_get_ns() / 1000;
    data.type = 4;
    events.perf_submit(ctx, &data, sizeof(data));
    return 0;
};

int kretprobe__pci_assign_resource(struct pt_regs *ctx) {
    struct data_t data = {};
    data.uenv = PT_REGS_RC(ctx);
    data.pid= bpf_get_current_pid_tgid();
    data.ts = bpf_ktime_get_ns() / 1000;
    data.type = 5;
    events.perf_submit(ctx, &data, sizeof(data));
    return 0;
};

int kprobe__device_create_file(struct pt_regs *ctx, struct device *dev, const struct device_attribute *attr) {
    struct data_t data = {};
    data.pid= bpf_get_current_pid_tgid();
    data.ts = bpf_ktime_get_ns() / 1000;
    data.type = 6;
    const char *tmp = attr->attr.name;
    bpf_probe_read(data.name,32,tmp);
    events.perf_submit(ctx, &data, sizeof(data));
    return 0;
};

int kretprobe__device_create_file(struct pt_regs *ctx, struct device *dev, const struct device_attribute *attr) {
    struct data_t data = {};
    data.uenv = PT_REGS_RC(ctx);
    data.pid= bpf_get_current_pid_tgid();
    data.ts = bpf_ktime_get_ns() / 1000;
    data.type = 7;
    events.perf_submit(ctx, &data, sizeof(data));
    return 0;
};
""")

blkn = 0
#header
#for kernel version 4.14.105-19-0017 
uenvstr = ["KOBJ_ADD", "KOBJ_REMOVE", "KOBJ_CHANGE", "KOBJ_MOVE", "KOBJ_ONLINE", "KOBJ_OFFLINE", "KOBJ_BIND", "KOBJ_UNBIND", "KOBJ_MAX"]
print("%-18s %-6s %s" % ("TIME(s)", "PID", "CALL"))

class Data(ct.Structure):
    _fields_ = [
        ("ts", ct.c_ulonglong),
        ("pid", ct.c_uint),
        ("type", ct.c_ubyte),
        ("uenv", ct.c_ubyte),
        ("virtn", ct.c_ubyte),
        ("name", ct.c_char * 32),
    ]

#process event
def print_event(cpu, data, size):
    global blkn
    #event = b["events"].event(data) 
    event = ct.cast(data, ct.POINTER(Data)).contents
    secd = (event.ts)/1000000 + BOOT_TIME
    msecd = (float(event.ts)/1000000) - ((int)(event.ts) / 1000000)
    time = secd + msecd
    
    d = datetime.fromtimestamp(time)
    dstr = d.strftime("%Y-%m-%d %H:%M:%S.%f    ")
    orit = str(float(event.ts)/1000000)
    dstr  = dstr + orit.ljust(18,' ')
    #dstr = tmps.ljust(32,' ')
    if (event.type == 0): 
	fstr = "hotplug irq: acpi_irq"
        print("%s\tpid %-6d %8s" % (dstr, 
        event.pid, fstr))
    #elif (event.type == 1):
    elif (event.type == 2):
	fstr = "find new device: pci_device_add, "
        print("%s\tpid %-6d %8s now virtio-dev: %-6d" % (dstr, 
        event.pid, fstr, event.virtn))
    elif (event.type == 3):
	fstr = "send uevent:"
        print("%s\tpid %-6d %8s uenv:%s name:%s" % (dstr, 
        event.pid, fstr, uenvstr[event.uenv], event.name))
    elif (event.type == 4):
        if (event.uenv == 0):
	    fstr = "virtblk_probe return OK"
        else:
	    fstr = "virtblk_probe return ERROR"
        print("%s\tpid %-6d %8s" % (dstr, 
        event.pid, fstr))
    elif (event.type == 5):
        if (event.uenv == 0):
	    fstr = "pci_assign_resource return OK"
        else:
	    fstr = "pci_assign_resource return ERROR"
        print("%s\tpid %-6d %8s" % (dstr, 
        event.pid, fstr))
    elif (event.type == 6):
	fstr = "enter device_create_file:"
        print("%s\tpid %-6d %8s %s" % (dstr, 
        event.pid, fstr, event.name))
    elif (event.type == 7):
        if (event.uenv == 0):
	    fstr = "device_create_file return OK"
        else:
	    fstr = "device_create_file return ERROR"
        print("%s\tpid %-6d %8s" % (dstr, 
        event.pid, fstr))
#        print("%24s     pid %-6d %8s, now device:6d" % (dstr, 
#        event.pid, fstr, event.data))

# loop
BOOT_TIME = 0
def init_system_boot_time():
        global BOOT_TIME
        with open('/proc/stat') as f:
                content = f.readlines()
                for e in content:
                        if e[:6] == 'btime ':
                                BOOT_TIME = int(e.split()[1])

        print('GET SYSTEM BOOT-TIME-STAMP:%u' % BOOT_TIME)

init_system_boot_time()

b["events"].open_perf_buffer(print_event)
while 1:
    try:
        b.perf_buffer_poll()
    except KeyboardInterrupt:
        exit()
