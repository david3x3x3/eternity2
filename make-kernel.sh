#!/bin/bash
awk 'BEGIN { printf "#define MYKERNEL 1\n" } /END_KERNEL/ { p=0 } p { print } /BEGIN_KERNEL/ { p=1 }' eternity2.c | grep -v '^ *//' | cat - mykernel.cl > eternity2_kernel.cl
