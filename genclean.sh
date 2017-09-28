#!/bin/bash
# 10 21 b10x10s1
# 7
set -x
for p in b10x10s1.10.17.85 b9x9s1.7.10.69 eternity.8.21.204; do
    p=$(echo $p | cut -d. -f1)
    for t in gen static; do
	rm -v \
	   $p-$t \
	   $p-$t-asmjs.js \
	   $p-$t-asmjs.js.mem \
	   $p-$t-asmjs.js.map \
	   $p-$t-wasm.asm.js \
	   $p-$t-wasm.js \
	   $p-$t-wasm.js.mem \
	   $p-$t-wasm.js.map \
	   $p-$t-wasm.wasm \
	   $p-$t-wasm.wast
    done
done
rm genheader1.c genheader2.c gensearch.c
