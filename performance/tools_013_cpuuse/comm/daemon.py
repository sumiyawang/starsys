__author__ = 'cloudyang'
# -*- coding: utf-8 -*-
import os
import sys


def daemon_init():
    try:
        #第一次fork,结束主进程，通知shell进程结束，子进程转入后台
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError,e:
        print >> stderr, "fork 1 failed : %s" % e.strerror
        sys.exit(1)
        
    #子进程创建一个新session,并变成session的leader,脱离原终端和session的控制
    os.setsid()
    try:
        #第二次fork,干掉session的leader(前一个子进程),使用新的子进程作为daemon进程,排除打开终端的可能性
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
        #设置根目录和文件权限掩码
        #os.chdir("/")
        os.umask(0)
        #关闭标准输入输出，重定向到/dev/null
        for fd in range(0,3):
            try:
                os.close(fd)
            except OSError,e:
                pass

        null_fd = os.open('/dev/null', os.O_RDWR)
        os.dup2(null_fd, 1);
        os.dup2(null_fd, 2);
    except OSError,e:
        print >> stderr, "fork 2 failed : %s" % e.strerror
        sys.exit(1)
