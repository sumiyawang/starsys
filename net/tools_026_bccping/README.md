For example: 
10.0.8.10 ping --> 10.0.8.15

```
in 10.0.8.10:

./bccping_send.py -i 10.0.8.15
2021-04-17 19:21:44.976447    360871.976447      ===> 1. create ping package in ip_output  271 src 10.0.8.10 dst 10.0.8.15
2021-04-17 19:21:44.976463    360871.976463      2. send ping at __dev_queue_xmit  271 delta(ms): 0.016
2021-04-17 19:21:44.976478    360871.976478      3. send ping at virtqueue_add_outbuf  271 delta(ms): 0.031
2021-04-17 19:21:44.994905    360871.994905      5. recv ping at __netif_receive_skb_core  271 delta(ms): 18.458
2021-04-17 19:21:44.994921    360871.994921      6. recv ping at __sock_queue_rcv_skb  271 delta(ms): 18.474
2021-04-17 19:21:44.994875    360871.994875      4. recv ping at napi_gro_receive  271 delta(ms): 18.428, Net link consume(ms): 18.397

in 10.0.8.15:

./bccping_recv.py -i 10.0.8.10
2021-04-17 19:21:45.411775    1388959.41177      ===> 1. recv ping package at napi_gro_receive  271 src 10.0.8.10 dst 10.0.8.15
2021-04-17 19:21:45.424769    1388959.42477      2. recv ping at __netif_receive_skb_core  271 delta(ms): 12.994
2021-04-17 19:21:45.424785    1388959.42479      3. recv ping at icmp_recv  271 delta(ms): 13.01
2021-04-17 19:21:45.424798    1388959.4248       4. send ping at ip_output  271 delta(ms): 13.023
2021-04-17 19:21:45.424802    1388959.4248       5. send ping at __dev_queue_xmit  271 delta(ms): 13.027
2021-04-17 19:21:45.424814    1388959.42481      6. send ping at virtqueue_add_outbuf  271 delta(ms): 13.039

即可看出ping 抖动来自目的端的 napi_gro_receive -> __netif_receive_skb_core，两函数之间耗时12.994
而这两函数异常说明RPS软中断唤醒的慢了
而抓包点在__netif_receive_skb_core之后，所抓包看不出来该问题
针对以上函数可参见vhost-kernel架构分析：http://km.oa.com/group/36284/articles/show/448163

可选参数：-g n
只统计大于 n 微秒的 ping 包，不指定则全部统计
可结合tools_005_bcc-vring查看vring处理速度
```



