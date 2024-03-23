#!/bin/bash
i=0
j=1
num=$2
dir=$1
rm -rf $dir
mkdir $dir
for((i=1;i<=$num;++i))
do
    echo "XXX$i" > $dir/$i
done
sync
tar -zcf $dir.tgz $dir/
rm -rf $dir
sync
sleep 5
cd /p2
tar -zxf $dir.tgz
rm $dir.tgz
sync

for((i=1;i<=$num;++i))
do
    var=`cat $dir/$i`
    if [ "$var" != "XXX$i" ];then
        echo "error: $dir/$i $var"
        exit 1
    fi
done
echo done >> /p2/${dir}.log
touch ok$dir
