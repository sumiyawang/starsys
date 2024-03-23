arg1: -p pid
[options:]
arg2: -i time window
arg3: -t tid

usage: watch the process/threads runtime and percent in every time window

[root@kvm_10_53_70_76 /data/run]# ./cpustat.py -p 6739
sleeping
process launch time: 2021-03-31 18:36:23.860000    
total thread: 5
thread:   6739 total usrtime 0.00 systime 0.00
thread:   6740 total usrtime 0.04 systime 11.17
thread:   6741 total usrtime 0.05 systime 11.18
thread:   6742 total usrtime 0.06 systime 11.33
thread:   6743 total usrtime 0.05 systime 11.23

last 1 sec pid 6739: cpu 371.00% sys 99.19%
thread   6739 usr 0.00(0.00%) sys 0.00(0.00%)
thread   6740 usr 0.01(1.02%) sys 0.97(98.98%)
thread   6741 usr 0.01(1.11%) sys 0.89(98.89%)
thread   6742 usr 0.01(1.11%) sys 0.89(98.89%)
thread   6743 usr 0.01(1.06%) sys 0.93(98.94%)

[root@VM-8-3-centos run]# ./cpustat.py -p 431706 -i 5 -t 431707,431708-431710
sleeping
process launch time: 2021-03-31 19:35:18.570000    
total thread: 5
thread: 431707 total usrtime 96.21 systime 683.98
thread: 431708 total usrtime 94.23 systime 686.09
thread: 431709 total usrtime 94.59 systime 685.46
thread: 431710 total usrtime 94.72 systime 685.21

last 5 sec pid 431706: cpu 394.20% sys 87.27%
thread: 431707 usr 0.62(12.58%) sys 4.31(87.42%)
thread: 431708 usr 0.63(12.80%) sys 4.29(87.20%)
thread: 431709 usr 0.62(12.60%) sys 4.30(87.40%)
thread: 431710 usr 0.64(12.98%) sys 4.29(87.02%)

last 5 sec pid 431706: cpu 394.60% sys 87.53%
thread: 431707 usr 0.65(13.21%) sys 4.27(86.79%)
thread: 431708 usr 0.59(11.94%) sys 4.35(88.06%)
thread: 431709 usr 0.61(12.37%) sys 4.32(87.63%)
thread: 431710 usr 0.62(12.53%) sys 4.33(87.47%)
