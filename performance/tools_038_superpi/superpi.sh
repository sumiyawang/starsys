#!/bin/bash

begin=$1
end=$2

for ((i=begin;i<=end;i++))
do
    echo $i
    time echo "scale=5000;4*a(1)"| taskset -c $i bc -l -q &>/dev/null &
done
