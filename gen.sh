#!/bin/bash
# 10 21 b10x10s1
# 7
set -x
for p in b10x10s1.10.17.85 b9x9s1.7.10.69 eternity2.0.999.0; do
    p1=$(echo $p | cut -d. -f2)
    p2=$(echo $p | cut -d. -f3)
    p3=$(echo $p | cut -d. -f4)
    p=$(echo $p | cut -d. -f1)
    for t in static gen; do
	./eternity2 -gen $p1 $p2 $p3 $p | awk '/^int/ { p=1 } !p { print }' | sed 's/__constant //' > genheader1.c
	./eternity2 -gen $p1 $p2 $p3 $p | grep ^int > genheader2.c
	if [ $t = "gen" ]; then
  	    ./eternity2 -gen $p1 $p2 $p3 $p | awk '/^POS/ { p=1 } p { print }' > gensearch.c
	else
	    cp static.c gensearch.c
	fi
	emcc -s BINARYEN=1 -s EXPORTED_FUNCTIONS=_main,_origmain -s EXPORTED_RUNTIME_METHODS=ccall -O2 -o $p-$t-wasm.js eternitygen.c
	#gcc -O6 -o $p-$t eternitygen.c
	#x86_64-w64-mingw32-gcc -O6 -o $p-$t eternitygen.c
    done
done
