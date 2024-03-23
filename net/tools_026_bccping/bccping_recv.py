#!/usr/bin/python

from __future__ import print_function
from bcc import BPF
import time
from datetime import datetime
from time import sleep
import os
import socket
import struct
import sys, getopt
import binascii
import argparse

intip = 0


#BPF
bpf_code = """

#include <linux/kobject.h>
#include <linux/netdevice.h>
#include <linux/etherdevice.h>
#include <linux/ethtool.h>

#define MAC_HEADER_SIZE 14
struct data_t {
    u64 ts;
    u32 pid;
    u8 type;
    u16 data1;
    u64 data2;
    u64 src;
    u64 dst;
    char name[32];
};

struct time_t {
    u64 ts;
    u16 seq;
    u64 t1;
    u64 t2;
    u64 t3;
    u64 t4;
    u64 t5;
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

struct icmphdr {
  __u8          type;
  __u8          code;
  __sum16       checksum;
  union {
        struct {
                __be16  id; 
                __be16  sequence;
        } echo;
        __be32  gateway;
        struct {
                __be16  __unused;
                __be16  mtu;
        } frag;
  } un; 
};

struct iphdr {
        __u8    ihl:4,
                version:4;
        __u8    tos;
        __be16  tot_len;
        __be16  id; 
        __be16  frag_off;
        __u8    ttl;
        __u8    protocol;
        __sum16 check;
        __be32  saddr;
        __be32  daddr;
        /*The options start here. */
};



BPF_PERF_OUTPUT(events);
BPF_HISTOGRAM(distsd);

BPF_HASH(grocv, u16, u64);  //key: irq number  value: virtn
BPF_HASH(skbcore, u16, u64);  //key: irq number  value: virtn
BPF_HASH(icv, u16, u64);  //key: irq number  value: virtn
BPF_HASH(ipout, u16, u64);  //key: irq number  value: virtn
BPF_HASH(qxmit, u16, u64);  //key: irq number  value: virtn
BPF_HASH(outbuf, u16, u64);  //key: irq number  value: virtn

int kprobe__ip_output(struct pt_regs *ctx,OSV struct sock *sk, struct sk_buff *skb)
{
    struct data_t data = {};
    data.ts = bpf_ktime_get_ns() / 1000;
    struct icmphdr *icmph;
    icmph = (struct icmphdr *)(skb->head + skb->transport_header);

    if (icmph->type == 0) {
        u16 tmp;
        bpf_probe_read(&tmp,2,&icmph->un.echo.sequence);
        data.data1 = ntohs(tmp);
        data.type = 3;

        //qxmit.update(&tmp, &data.ts);
        u64 *outt = grocv.lookup(&tmp);
        if (outt == NULL) {
            return 0;
        } else {
            data.data2 = data.ts - *outt;
            ipout.update(&tmp, &data.data2);
        }
        //events.perf_submit(ctx, &data, sizeof(data));
    }

    return 0;
}

int kprobe____dev_queue_xmit(struct pt_regs *ctx, struct sk_buff *skb)
{
    struct data_t data = {};
    data.ts = bpf_ktime_get_ns() / 1000;
    struct icmphdr *icmph;
    icmph = (struct icmphdr *)(skb->head + skb->transport_header);

    if (icmph->type == 0) {
        u16 tmp;
        bpf_probe_read(&tmp,2,&icmph->un.echo.sequence);
        data.data1 = ntohs(tmp);
        data.type = 4;

        u64 *outt = grocv.lookup(&tmp);
        if (outt == NULL) {
            return 0;
        } else {
            data.data2 = data.ts - *outt;
            qxmit.update(&tmp, &data.data2);
        }
        //events.perf_submit(ctx, &data, sizeof(data));
    }

    return 0;
    

}

int kprobe__virtqueue_add_outbuf(struct pt_regs *ctx, struct virtqueue *vq, 
				struct scatterlist *sg, unsigned int num,
				struct sk_buff *skb)
{

    struct data_t data = {};
    struct time_t times = {};
    data.ts = bpf_ktime_get_ns() / 1000;
    times.ts = data.ts;
    struct icmphdr *icmph;
    icmph = (struct icmphdr *)(skb->head + skb->transport_header);

    if (icmph->type == 0) {
        u16 tmp;
        bpf_probe_read(&tmp,2,&icmph->un.echo.sequence);
        data.data1 = ntohs(tmp);
        times.seq = data.data1;
        data.type = 5;

        u64 *outt = grocv.lookup(&tmp);
        if (outt == NULL) {
            return 0;
        } else {
            times.t5 = data.ts - *outt;
            if (times.t5 < HIGHTIME) {
                grocv.delete(&tmp);
                skbcore.delete(&tmp);
                icv.delete(&tmp);
                ipout.delete(&tmp);
                qxmit.delete(&tmp);
                return 0;
            }
        }
        outt = skbcore.lookup(&tmp);
        if (outt == NULL) {
            times.t1 = 0;
        } else {
            times.t1 = *outt;
        }
        outt = icv.lookup(&tmp);
        if (outt == NULL) {
            times.t2 = 0;
        } else {
            times.t2 = *outt;
        }
        outt = ipout.lookup(&tmp);
        if (outt == NULL) {
            times.t3 = 0;
        } else {
            times.t3 = *outt;
        }
        outt = qxmit.lookup(&tmp);
        if (outt == NULL) {
            times.t4 = 0;
        } else {
            times.t4 = *outt;
        }
        events.perf_submit(ctx, &times, sizeof(times));

        grocv.delete(&tmp);
        skbcore.delete(&tmp);
        icv.delete(&tmp);
        ipout.delete(&tmp);
        qxmit.delete(&tmp);
    }

    return 0;
};

int kprobe__icmp_rcv(struct pt_regs *ctx, struct sk_buff *skb)
{
    struct data_t data = {};
    data.ts = bpf_ktime_get_ns() / 1000;
    struct icmphdr *icmph;
    icmph = (struct icmphdr *)(skb->head + skb->transport_header);

    if (icmph->type == 8) {
        u16 tmp;
        bpf_probe_read(&tmp,2,&icmph->un.echo.sequence);
        data.data1 = ntohs(tmp);
        data.type = 2;

        u64 *outt = grocv.lookup(&tmp);
        if (outt == NULL) {
            return 0;
        } else {
            data.data2 = data.ts - *outt;
            icv.update(&tmp, &data.data2);
        }
        //events.perf_submit(ctx, &data, sizeof(data));
    }

    return 0;
}

int kprobe__napi_gro_receive(struct pt_regs *ctx, struct napi_struct *napi, struct sk_buff *skb)
{
    struct data_t data = {};
    data.ts = bpf_ktime_get_ns() / 1000;
    struct iphdr iphdr;
    struct icmphdr icmphdr;

    //l3 means ip level
    u8 *l3_header_address;
    //l4 means transfer level
    u8 *l4_header_address;

    unsigned char *head = skb->head;
    u16 mac_header = skb->mac_header;
    u16 network_header = skb->network_header;

    if (network_header == 0) {
        network_header = mac_header + MAC_HEADER_SIZE;
    }   
    
    l3_header_address = head + network_header; 

    bpf_probe_read(&iphdr, sizeof(iphdr), l3_header_address);
    if (SRCIP != iphdr.saddr)
        return 0;

    if (iphdr.protocol == IPPROTO_ICMP) {
        l4_header_address = l3_header_address + iphdr.ihl * 4;
        bpf_probe_read(&icmphdr, sizeof(icmphdr), l4_header_address);
        u16 tmp = icmphdr.un.echo.sequence;
        data.data1 = ntohs(tmp);
        data.type = 0;
        data.src = iphdr.saddr;
        data.dst = iphdr.daddr;
        grocv.update(&tmp, &data.ts);
        //events.perf_submit(ctx, &data, sizeof(data));
    }

    return 0;

};

int kprobe____netif_receive_skb_core(struct pt_regs *ctx, struct sk_buff *skb)
{
    struct data_t data = {};
    data.ts = bpf_ktime_get_ns() / 1000;
    struct iphdr iphdr;
    struct icmphdr icmphdr;

    //l3 means ip level
    u8 *l3_header_address;
    //l4 means transfer level
    u8 *l4_header_address;

    unsigned char *head = skb->head;
    u16 mac_header = skb->mac_header;
    u16 network_header = skb->network_header;

    if (network_header == 0) {
        network_header = mac_header + MAC_HEADER_SIZE;
    }   
    
    l3_header_address = head + network_header; 

    bpf_probe_read(&iphdr, sizeof(iphdr), l3_header_address);

    if (iphdr.protocol == IPPROTO_ICMP) {
        l4_header_address = l3_header_address + iphdr.ihl * 4;
        bpf_probe_read(&icmphdr, sizeof(icmphdr), l4_header_address);
        u16 tmp = icmphdr.un.echo.sequence;
        data.data1 = ntohs(tmp);
        data.type = 1;
        u64 *outt = grocv.lookup(&tmp);
        if (outt == NULL) {
            return 0;
        } else {
            data.data2 = data.ts - *outt;
            skbcore.update(&tmp, &data.data2);
        }
        //events.perf_submit(ctx, &data, sizeof(data));
    }

    return 0;

}

"""

def big_small_end_convert(data):
    return binascii.hexlify(binascii.unhexlify(data)[::-1])

#this for event debug
def print_event(cpu, times, size):
    event = b["events"].event(times) 
    secd = (event.ts)/1000000 + BOOT_TIME
    msecd = (float(event.ts)/1000000) - ((int)(event.ts) / 1000000)
    time = secd + msecd
    
    d = datetime.fromtimestamp(time)
    dstr = d.strftime("%Y-%m-%d %H:%M:%S.%f    ")
    orit = str(float(event.ts)/1000000)
    dstr  = dstr + orit.ljust(18,' ')
    seq = event.seq
    
    print("\n%s" % dstr)
    fstr = "===> 1. recv ping package at napi_gro_receive"
    print("%s seq:%4d" % (fstr, event.seq))
    fstr = "2. recv ping at __netif_receive_skb_core"
    delta = str(float(event.t1)/1000)
    print("%s seq:%4d delta(ms):%s" % (fstr,seq, delta))
    fstr = "3. recv ping at icmp_recv"
    delta = str(float(event.t2)/1000)
    print("%s seq:%4d delta(ms):%s" % (fstr,seq, delta))
    fstr = "4. send ping at ip_output"
    delta = str(float(event.t3)/1000)
    print("%s seq:%4d delta(ms):%s" % (fstr,seq, delta))
    fstr = "5. send ping at __dev_queue_xmit"
    delta = str(float(event.t4)/1000)
    print("%s seq:%4d delta(ms):%s" % (fstr,seq, delta))
    fstr = "6. send ping at virtqueue_add_outbuf"
    delta = str(float(event.t5)/1000)
    print("%s seq:%4d delta(ms):%s" % (fstr,seq, delta))

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



hight = 1
def myopts(argv):
    global intip
    global hight
    try:
        opts, args = getopt.getopt(argv,"hi:g:")
    except getopt.GetoptError:
       print("./bccping_recv.py -i ip (dst)")
       exit()
    for opt, arg in opts:
        if opt == '-i':
            oriip = arg
            intip = socket.ntohl(struct.unpack(">I",socket.inet_aton(str(oriip)))[0])
            src = socket.inet_ntoa(struct.pack("<I",intip))
            print("FILTER SRC ip: %s" % src)
        elif opt == '-h':
            print("./bccping_recv.py -i ip (dst) [ -g high_time(us)]")
            exit()
        elif opt == '-g':
            hight = arg

myopts(sys.argv[1:])

if intip == 0:
    print("valid arg: -i ip")
    exit()
else:
    bpf_code = bpf_code.replace('SRCIP', '%s' % intip)

res = os.popen('uname -r|cut -c 1')
for n in res.readlines():
    kv = int(n)
    if kv <= 3:
        bpf_code = bpf_code.replace('OSV', '')
    else:
        bpf_code = bpf_code.replace('OSV', 'struct net *net,')
    break
bpf_code = bpf_code.replace('HIGHTIME', '%s' % hight)
    

b = BPF(text=bpf_code)
b["events"].open_perf_buffer(print_event)

while 1:
    try:
        b.perf_buffer_poll()
    except KeyboardInterrupt:
        exit()
