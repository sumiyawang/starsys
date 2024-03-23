#bin/bash
while true
do
    mkfs.ext4 /dev/vdc > /dev/null
    mount /dev/vdc /p2
    cp checkdir.sh /p2
    cd /p2
    sh checkdir.sh dir1 50000 > /p2/log1 &
    sh checkdir.sh dir2 1000 > /p2/log2 &
    sh checkdir.sh dir3 10000 > /p2/log3 &
    while true
    do
        sleep 2
        ls /p2/okdir1 > /dev/null 2>&1
        [[ $? -ne 0 ]] && continue
        ls /p2/okdir2 > /dev/null 2>&1
        [[ $? -ne 0 ]] && continue
        ls /p2/okdir3 > /dev/null 2>&1
        [[ $? -ne 0 ]] && continue
        break
    done
    cd /root
    umount /p2
    mkfs.ext4 /dev/vdc
    echo "rount $i ok"
    ((++i))
done
