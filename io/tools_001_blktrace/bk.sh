#!/bin/sh
dir=$(cd `dirname $0`;pwd)
disk=$1
[[ ! -n "$disk" ]] && echo "no disk" && exit 1
dev=`echo $disk|awk -F '/' '{print $NF}'`
stime=$2
[[ ! -n "$stime" ]] && echo "default 10" && stime=10

mkdir $dir/qcloud_blktrace

cd $dir/qcloud_blktrace

if [ -f "/usr/bin/cgexec" ];then
    chrt -p -r 50 $$
    cgexec -g cpuset:/ timeout $stime blktrace -d $disk 1>/dev/null
else
    timeout $stime blktrace -d $disk 1>/dev/null
fi

blkparse -i $dev -d $dev.blktrace.bin 1>/dev/null 2>&1

btt -i $dev.blktrace.bin > $dir/qcloud_blktrace/blklog
echo "blktrace result saved in $dir/qcloud_blktrace/blklog"
