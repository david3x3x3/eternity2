#!/bin/bash
# 10 21 b10x10s1
# 7
set -x
for p in b10x10s1.10.17.85 b9x9s1.7.10.69 eternity.8.21.204; do
    p1=$(echo $p | cut -d. -f2)
    p2=$(echo $p | cut -d. -f3)
    p3=$(echo $p | cut -d. -f4)
    p=$(echo $p | cut -d. -f1)
    for t in gen static; do
	./eternity2 -gen $p1 $p2 $p3 $p | awk '/^int/ { p=1 } !p { print }' | sed 's/__constant //' > genheader1.c
	./eternity2 -gen $p1 $p2 $p3 $p | grep ^int > genheader2.c
	if [ $t = "gen" ]; then
  	    ./eternity2 -gen $p1 $p2 $p3 $p | awk '/^POS/ { p=1 } p { print }' > gensearch.c
	else
	    cp static.c gensearch.c
	fi
	emcc -s EXPORTED_FUNCTIONS="['_main','_origmain']" -O2 -o $p-$t-asmjs.js eternitygen.c
	emcc -s BINARYEN=1 -s "BINARYEN_METHOD='native-wasm,interpret-s-expr,interpret-binary,interpret-asm2wasm'" -s EXPORTED_FUNCTIONS="['_main','_origmain']" -O2 -o $p-$t-wasm.js eternitygen.c
	gcc -O6 -o $p-$t eternitygen.c
    done
done
