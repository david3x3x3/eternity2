#!/bin/bash
while :; do
    n=$RANDOM
    n2=$(awk "/ 6210 / { print \$1 }" 10x10-6210-list.txt | awk "NR == $RANDOM { print }")
    if [ $n -gt 32640 -o -f 10x10/$n2.log ]; then
	continue
    fi
    python solve.py pieces_set_1/pieces_10x10.txt 10 $n2 2>&1 | tee 10x10/$n2.log
done
