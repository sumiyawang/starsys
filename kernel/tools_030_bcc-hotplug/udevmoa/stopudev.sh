#!/bin/bash

pid=`ps ax|grep bccattach.py|grep -v grep|awk '{print $1}'`
if [ -n "$pid" ];then
    kill -9 $pid
fi

pid=`ps ax|grep "udevadm monitor"|grep -v grep|awk '{print $1}'`
if [ -n "$pid" ];then
    kill -9 $pid
fi
