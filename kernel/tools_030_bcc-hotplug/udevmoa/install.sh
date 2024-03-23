#!/bin/bash
dir=$(cd `dirname $0`;pwd)
bcclog=$dir/bcclog
moalog=$dir/moalog

yum install -y bcc-tools
if [ $? -ne 0 ];then
    echo "install bcc env failed"
    exit 1
fi

chmod +x ./bccattach.py

stdbuf -o0 ./bccattach.py >> $bcclog &
stdbuf -o0 udevadm monitor >> $moalog &

sleep 3 
runp=$(ps ax|grep "bccattach.py"|grep -v grep)
if [ ! -n "$runp" ];then
    echo "bcc launch failed"
    exit 1
fi

runp=$(ps ax|grep "udevadm monitor"|grep -v grep)
if [ ! -n "$runp" ];then
    echo "udevadm monitor launch failed"
    exit 1
fi

echo "install ok"
