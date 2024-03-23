目前只接收一个参数./bccvring.py -s time 

适用：centos7 系列，其它内核版本需要分别适配

统计了vring这几个指标的分布：

1，recv-Q 的 used->idx - last_used_idx，差值越大表示前端处理越慢

2，send-Q 的 avaid->idx - used->idx，差值越大表示后端越弱

统计了max，可根据max的值看出是否有抖动

此外该工具还统计了send-Q的free buf的能力，virtqueue_kick的次数，num_free的最小值

性能损失在3%~5%之间，可常驻运行



```
[root@VM-32-120-centos ~]# ./bccvring.py -s 10
start tracing...
Note: vring distance = used->idx - last_used_idx, bigger means worse

recv-Q consume pkg cap: (used->idx - last_used_idx)
     recv-Q distance     : count     distribution
         0 -> 1          : 621951   |****************************************|
         2 -> 3          : 52278    |***                                     |
         4 -> 7          : 212157   |*************                           |
         8 -> 15         : 350003   |**********************                  |
        16 -> 31         : 53316    |***                                     |
max: 23 

send-Q send pkg cap: (avaid->idx - used->idx)
     send-Q put more     : count     distribution
         0 -> 1          : 1202785  |****************************************|
         2 -> 3          : 61797    |**                                      |
         4 -> 7          : 21527    |                                        |
         8 -> 15         : 2441     |                                        |
        16 -> 31         : 62       |                                        |
max: 22 

send-Q free pkg cap: (used->idx - last_used_idx)
     send-Q distance     : count     distribution
         0 -> 1          : 1286107  |****************************************|
         2 -> 3          : 2237     |                                        |
         4 -> 7          : 317      |                                        |
         8 -> 15         : 49       |                                        |
        16 -> 31         : 3        |                                        |

virtqueue_kick total: 1289210 
min numfree in send-Q: 1002 
min numfree in recv-Q: 1 
```

