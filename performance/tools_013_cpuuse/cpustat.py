#!/usr/bin/python

import re
import os
import sys, getopt
import copy
import time
import traceback,datetime
from datetime import datetime

# ##only for debug
if __name__ == "__main__":
    try:
        sys.path.append(os.getcwd() + '/comm/')
    except Exception, e:
        sys.stderr.write("Set Module Directory Failed")
        sys.exit(1)

import constant

import psutil
def main(argv):
    on = False
    intr = 1
    highp = 1
    watch_tr = False
    show_high = False
    aim_thr = []
    try:
        opts, args = getopt.getopt(argv,"hp:i:t:g:")
    except getopt.GetoptError:
       print './cpustat.py -p PID [ -i time -t tid1,tid2-tidn -g high ]'
       exit()
    for opt, arg in opts:
        if opt == '-h':
            print './cpustat.py -p PID [ -i time -t tid1,tid2-tidn -g high ]'
            exit()
        elif opt in ("-p"):
            pid = int(arg)
            on = True
        elif opt in ("-i"):
            intr = int(arg)
        elif opt in ("-g"):
            highp = int(arg)
            show_high = True
        elif opt in ("-t"):
            arg_thr = arg.split(',')
            for parg in arg_thr:
                ab = parg.split('-')
                if len(ab) == 2:
                    for i in range(int(ab[0]), 1+int(ab[1])):
                        aim_thr.append(i)
                else:
                    aim_thr.append(int(ab[0]))
            watch_tr = True
    if on == False:
        print("no pid to monitor")
        print './cpustat.py -p PID'
        exit()
    p = psutil.Process(pid)
    
    thtime = {}
    comms = {}
    print(p.status())
    ltime = p.create_time()
    d = datetime.fromtimestamp(ltime)
    dstr = d.strftime("%Y-%m-%d %H:%M:%S.%f    ")
    print("process launch time: %s" % dstr)
    print("total thread: %d" % p.num_threads())
    lastc = p.cpu_times()
    th = p.threads()
    for key,usr,sys in th:
        if watch_tr and key not in aim_thr:
            continue
        thtime[key] = usr,sys
        print("thread: %6d total usrtime %.2f systime %.2f" % (key,usr,sys))
    try:
        while 1:
            time.sleep(intr)
            th = p.threads()
            nowc = p.cpu_times()
            total = nowc[0] + nowc[1]
            runtime = total - (lastc[0] + lastc[1])
            if runtime == 0:
                delt = 0
                delt_sys = 0
            else:
                delt = 100*runtime/intr
                delt_sys = 100*(nowc[1] - lastc[1])/runtime
            lastc = nowc
            print("")
            print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
            print("last %d sec pid %d: cpu %.2f%% sys %.2f%%" % (intr,pid, delt, delt_sys))
            for key,usr,sys in th:
                try:
                    res = os.popen("cat /proc/%d/task/%d/comm" % (pid, key))
                    for comm in res.readlines():
                        com = comm.replace('\n', '')
                        break
                except:
                    com = "null"
                if watch_tr and key not in aim_thr:
                    continue
                try:
                    thv = thtime[key]
                except:
                    thtime[key] = usr, sys
                nowusr = usr - thv[0]
                nowsys = sys - thv[1]
                total = nowusr + nowsys
                tcpu = 100*total/intr
                if total <= 0.1:
                    r_usr = 0
                    r_sys = 0
                else:
                    r_usr = 100*(nowusr/total)
                    r_sys = 100*(nowsys/total)
                if show_high:
                    if r_sys >= highp:
                        print("%s thread: %6d CPU %.2f%% usr %.2f(%.2f%%) sys %.2f(%.2f%%)" % (com, key, tcpu, nowusr, r_usr, nowsys, r_sys))
                else:
                    print("%s thread: %6d CPU %.2f%% usr %.2f(%.2f%%) sys %.2f(%.2f%%)" % (com, key, tcpu, nowusr, r_usr, nowsys, r_sys))
                thtime[key] = usr,sys
    except KeyboardInterrupt:
        print("")
        exit()

main(sys.argv[1:])
