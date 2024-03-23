### vring队列crash调试方法

centos7子机debuginfo安装 

wget http://mirrors.tencentyun.com/centos-debuginfo/7/x86_64/kernel-debuginfo-3.10.0-1160.11.1.el7.x86_64.rpm
wget http://mirrors.tencentyun.com/centos-debuginfo/7/x86_64/kernel-debuginfo-common-x86_64-3.10.0-1160.11.1.el7.x86_64.rpm

#### 子机内virtio-net

1，crash 命令

```
crash> mod -S
crash> net
   NET_DEVICE     NAME   IP ADDRESS(ES)
ffff88040d2f4000  lo     127.0.0.1
ffff8800da2f8000  eth0   10.144.68.100
```

net_device地址：ffff8800da2f8000

2，*net_device |grep SIZE

```
crash> *net_device -x|grep SIZE
SIZE: 0x840
```

检查addr(net_device)+sizeof(net_device)且32字节对齐后的首地址：ffff8800da2f8840

3，sendq，recvq的地址

```
crash> *virtnet_info.sq ffff8800da2f8840
  sq = 0xffff8804079bc000
crash> *virtnet_info.rq ffff8800da2f8840
  rq = 0xffff8804079be000
```

send_queue /receive_queue是数组，找对应的vring需要 addr+(队列号*SIZE)

4，以1号sendq队列0xffff8804079bc000的1号队列为例：

```
crash> px ((struct send_queue  *)0xffff8804079bc000)[1].vq
$19 = (struct virtqueue *) 0xffff880035420000
```

virtqueue和vring_virtqueue为同一地址

5，观察子机vring整体情况：

```
crash> *vring_virtqueue.vq.num_free,free_head,last_used_idx,avail_idx_shadow 0xffff880035420000
  vq.num_free = 1023,
  free_head = 1
  last_used_idx = 21777
  avail_idx_shadow = 21778
```

5.1 观察vring_avail：

```
crash> *vring_virtqueue.vring.avail 0xffff880035420000
  vring.avail = 0xffff88003541c000,
crash> *vring_avail.idx,ring 0xffff88003541c000
  idx = 21790,
  ring = 0xffff88003541c004
```

观察vring_avail.idx是否一直在变动

ring[idx]保存的是free_head地址，fring数组项结构为__virtio16，所以free_head可从这里得到：

```
px ((__virtio16  *)0xffff88003541c004)[21790%1024]
```

注：在随时变动的条件下，这种瞬态内容可能难以抓到

5.2 观察vring_used

```
crash> *vring_virtqueue.vring.used 0xffff880035420000
  vring.used = 0xffff88003541d000
crash> *vring_used.idx,ring 0xffff88003541d000
  idx = 9274
  ring = 0xffff88003541d004
```

观察vring_used.idx和last_used_idx的数量关系：在运行过程中应保持 idx > last_used_idx，表示后端处理完了，前端可以回收uesd，同时其差值也能反映子机处理包的性能，差值越多表示子机软中断处理的越慢

5.3 观察限速逻辑：

5.3.1 前端发送限速：

检查后端处理到哪个avail ring了（event_idx），为used ring的最后一个元素

```
crash> p ((struct vring_used_elem  *)0xffff88003541d004)[1024].id
$26 = 10380
```

本次加入的idx为vring_avail.idx，比较这两个值的差异，如果相差较大则前端可能不通知后端（比vring_avail.idx-num_added的差值小说明后端处理迅速，可通知）

5.3.2 后端限速前端：

前端把last_used_idx放到了avail ring的最后一个元素中：

```
crash> p ((struct __virtio16  *)0xffff88003541c004)[1024].id
```

注：限速需要配合flag：

VRING_USED_F_NO_NOTIFY（used->flags）

VRING_AVAIL_F_NO_INTERRUPT（avail->flags）

来管理通知，如果置位后这里限速无效



#### 子机内virtio-net收包

将sendq的地址改为recvq的地址，前端后端的消耗逻辑不变，只是从后端消耗满包变成了消耗空包

依然是前端使用virtqueue_add给desc，使用virtqueue_get_buf清desc

所以仍然可以关注以上的vring状态转换关系



#### 母机vhost-kernel vring 调试

```
crash> net
ffff881f8fa70000  veth_1E94BE16
```

net_device：ffff881f8fa70000

以子机收包为例，vhost为tx方向

首先需要通过veth的地址net_device拿到vhost_net的地址：

```
rpm2cpio kernel-debuginfo-3.10.0-693_44.tl2.x86_64.rpm |cpio -div
mod -s tun ./usr/lib/debug/lib/modules/3.10.0-693_44.tl2/kernel/drivers/net/tun.ko
mod -s vhost ./usr/lib/debug/lib/modules/3.10.0-693_44.tl2/kernel/drivers/vhost/vhost.ko
mod -s vhost_net ./usr/lib/debug/lib/modules/3.10.0-693_44.tl2/kernel/drivers/vhost/vhost_net.ko

crash> *net_device -x|grep SIZE
SIZE: 0x8c0
crash> *tun_struct.tfiles ffff881f8fa708c0
  tfiles = {0xffff885cfbf7b000, ...
  
crash> *tun_file.wq -ox 0xffff885cfbf7b000
struct tun_file {
  [ffff885cfbf7b340] struct socket_wq wq;
}
crash> *wait_queue_head_t.task_list ffff885cfbf7b340
  task_list = {
    next = 0xffff882e653d8e60, 
    prev = 0xffff882e653d8dd0
  }
```



0xffff882e653d8e60和0xffff882e653d8dd0 分别为收方向/发方向的callfunction地址



```
struct vhost_poll {
   [0x0] poll_table table;
  [0x10] wait_queue_head_t *wqh;
  [0x18] wait_queue_t wait;
  [0x40] struct vhost_work work;
  [0x80] unsigned long mask;
  [0x88] struct vhost_dev *dev;
}
SIZE: 0x90
crash> *wait_queue_t -ox
typedef struct __wait_queue {
   [0x0] unsigned int flags;
   [0x8] void *private;
  [0x10] wait_queue_func_t func;
  [0x18] struct list_head task_list;

crash> *vhost_net -ox
struct vhost_net {
     [0x0] struct vhost_dev dev;
    [0xb0] struct vhost_net_virtqueue vqs[2];
  [0x8da0] struct vhost_poll poll[2];
  [0x8ec0] unsigned int tx_packets;
  [0x8ec4] unsigned int tx_zcopy_err;
  [0x8ec8] bool tx_flush;
}
SIZE: 0x8ed0
```

由代码vhost_poll_init得0xffff882e653d8e60嵌在vhost_poll的wait的task_list内

所以得vhost_poll地址：0xffff882e653d8e60 - 0x30 = 0xffff882e653d8e30
vhost_net：0xffff882e653d8e30 -0x90 - 0x8da0 = 0xffff882e653d0000

vhost_net有两个ring，以VHOST_NET_VQ_TX为例

```
crash> *vhost_net -ox 0xffff882e653d0000 |grep vhost_net_virtqueue
  [ffff882e653d00b0] struct vhost_net_virtqueue vqs[2];
crash> *vhost_net_virtqueue -ox|grep SIZE
SIZE: 0x4678
RX vhost_net_virtqueue ffff882e653d00b0
TX vhost_net_virtqueue: ffff882e653d00b0 + 0x4678 = 0xffff882e653d4728
```

vhost_virtqueue ：ffff882e653d00b0

```
crash>  *vhost_net_virtqueue -ox ffff882e653d00b0 |grep vq
  [ffff882e653d00b0] struct vhost_virtqueue vq;
crash> *vhost_virtqueue.desc,avail,used,last_avail_idx,last_used_idx,signalled_used ffff882e653d00b0
  desc = 0x7f124c7b8000
  avail = 0x7f124c7bc000
  used = 0x7f124c7bc840
  last_avail_idx = 6672
  last_used_idx = 6672
  signalled_used = 6672
```

其中desc/avail/used的定义为用户态地址，crash这里访问不是很方便，可以看看iov的内容

同时可对比guest内的last_used_idx的值



