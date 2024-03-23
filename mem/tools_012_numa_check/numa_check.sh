#!/bin/bash

while getopts 'h' opt; do
    case $opt in
    h)  
       echo "sh numa_check.sh UUID"
       exit 0;;
    esac
done

UUID=$1
pid=$(cat /usr/local/var/run/libvirt/qemu/${UUID}.pid 2>/dev/null)
kerver=`uname -r |awk -F'-' '{print $1}'`
if [ ! -n "$pid" ];then
    echo "vm not running"
    exit 1
fi

NUMA=$(lscpu |grep -P node[0-9]|awk '{print $4}')

function locate_numa()
{
    local rang=$1 
    local scpu=$2
    
    local nx=$(echo $rang|awk 'BEGIN{RS=",";} { print $0 }')

    for sets in $nx
    do 
        [[ "$sets" == "$scpu" ]] && return 0
    done

    for sets in $nx
    do 
        #echo "sets $sets"
        echo $sets |grep "-" 1>/dev/null
        if [ $? -eq 0 ];then
            nstart=$(echo $sets|awk -F '-' '{print $1}')
            nend=$(echo $sets|awk -F '-' '{print $2}')
            #echo "s $nstart e $nend"
            if [ "$scpu" -ge "$nstart" ] && [ "$scpu" -le "$nend" ];then
                return 0
            fi
        else
            continue
        fi
    done
    return 1
}

function innuma()
{
    cpu=$1
    i=0
    for hset in $NUMA
    do
        locate_numa $hset $cpu
        if [ $? -eq 0 ];then
            echo "    Node $i"
            return 0
        fi
        ((++i))
    done
}

function cvm_numa()
{
    local uuid=$1
    echo "CVM vcpupin:($uuid)"
    ret=$(virsh vcpupin $uuid 2>&1|grep -Po "[0-9]+: [0-9\-,]+"|awk '{print "    "$2}'|sort|uniq)
    echo "$ret"
    sets=$(virsh vcpupin $uuid 2>&1|grep -Po "[0-9]+: [0-9\-,]+"|awk '{print $2}'|grep -Po "[0-9]+"|sort|uniq)
    echo "    included in Nodes:"
    for cpu in $sets
    do
        innuma $cpu
        [[ $? -eq 0 ]] && continue
    done|sort|uniq
}

function cvm_memory()
{
    echo "CVM memory(GB) malloced in:($UUID)"
    local dpdk=$(virsh dumpxml $UUID|grep "memAccess='shared'")
    [[ -n "$dpdk" ]] && echo "(DPDK CVM)"
    if [ "$kerver" = "2.6.32" ];then #KVM 1.0
        cat /proc/$pid/numa_maps|grep -v file|grep -Po "N[0-9]+=[0-9]+"|awk -F'=' '{sum[$1]=sum[$1]+$2}END{for(e in sum){print "    "e": "sum[e]*4/1024/1024.0}}'|sed -e 's/N/Node /g'
    else
        cat /proc/$pid/numa_maps|grep -Po "N[0-9]+=[0-9]+|kernelpagesize_kB=[0-9]+"|tac|awk -F'=' '{if($0 ~ /kernelpagesize_kB/){unit=$2;} else {sum[$1]=sum[$1]+$2*unit}}END{for(e in sum){print "    "e": "sum[e]/1024/1024}}'|sed -e 's/N/Node /g'
    fi
}

function taskset_uuid
{
    echo "Qemu process taskset in:($UUID)"
    ts=$(taskset -pc $pid|awk '{print $NF}')
    echo "    $ts"
    ts=$(echo $ts|grep -Po "[0-9]+"|sort|uniq)
    
    echo "    included in Nodes:"
    for cpu in $ts
    do
        innuma $cpu
    done|sort|uniq
}

function buddy_info
{
    
    buddys=$(cat /proc/buddyinfo |grep -v DMA|awk '{mult=4096;totals=0;for(i=5;i<=NF;i++){totals+=$i*mult;mult*=2;}print totals/1073741824;}')
    if [ "$kerver" = "2.6.32" ];then #KVM 1.0
        echo "(KVM 1.0)"
        buddys=$(cat /proc/buddyinfo |grep -v DMA|awk '{mult=2097152;totals=0;for(i=NF-1;i<=NF;i++){totals+=$i*mult;mult*=2;}print totals/1073741824.0;}')
        tbuddys=$(cat /proc/buddyinfo |grep -v DMA|awk '{mult=4096;totals=0;for(i=5;i<=NF;i++){totals+=$i*mult;mult*=2;}print totals/1073741824;}')
    fi
    i=0
    echo "OS node free(GB):"
    for bud in $buddys
    do
        echo "    Node $i $bud"
        ((++i))
    done
    i=0
    if [ "$kerver" = "2.6.32" ];then #KVM 1.0
        echo "KVM 1.0 OS total free(GB):"
        for bud in $tbuddys
        do
            echo "    Node $i $bud"
            ((++i))
        done
    fi
    local cached=`cat /proc/meminfo |grep -i ^Cached|grep -Po [0-9]+`
    local buffer=`cat /proc/meminfo |grep -i ^Buffer|grep -Po [0-9]+`
    local total=$(($cached+$buffer))
    local tg=$(echo $total|awk '{print $1/1048576}')
    echo "OS cache(GB): $tg"
}

cvm_numa $UUID
cvm_memory $UUID
taskset_uuid $UUID
buddy_info
echo "===================================================="
cat /proc/buddyinfo
echo "Static XML:"
cat /etc/vm/$UUID.xml|grep -E "memory mode|memnode cellid|topology|cell |vcpu "
echo "Running XML:"
virsh dumpxml $UUID|grep -E "memory mode|memnode cellid|topology|cell |vcpu "
mem=$(virsh dumpxml $UUID|grep "memory unit"|grep -Po [0-9]+|awk '{print $1/1048576}')
echo "CVM total memory(GB): $mem"


