#!/bin/bash
while :; do
    n2=$(< 10x10-5220-list.txt shuf -n1 | cut -d" " -f1)
    python solve.py --puzzle 10x10_1 --partial 10,$n2 2>&1 | tee 10x10/$n2.log
done
