#!/bin/bash
# 10 21 b10x10s1
# 7
set -x
./eternity2 -gen 10 17 85 b10x10s1 | awk '/^int/ { p=1 } !p { print }' | sed 's/__constant //' > genheader1.c
./eternity2 -gen 10 17 85 b10x10s1 | grep ^int > genheader2.c
./eternity2 -gen 10 17 85 b10x10s1 | awk '/^POS/ { p=1 } p { print }' > gensearch.c
emcc -s EXPORTED_FUNCTIONS="['_main','_origmain']" -O2 -o b10x10s1.js eternitygen.c
gcc -O6 -o b10x10s1 eternitygen.c
./eternity2 -gen 7 10 69 b9x9s1 | awk '/^int/ { p=1 } !p { print }' | sed 's/__constant //' > genheader1.c
./eternity2 -gen 7 10 69 b9x9s1 | grep ^int > genheader2.c
./eternity2 -gen 7 10 69 b9x9s1 | awk '/^POS/ { p=1 } p { print }' > gensearch.c
emcc -s EXPORTED_FUNCTIONS="['_main','_origmain']" -O2 -o b9x9s1.js eternitygen.c
gcc -O6 -o b9x9s1 eternitygen.c
./eternity2 -gen 8 21 204 eternity | awk '/^int/ { p=1 } !p { print }' | sed 's/__constant //' > genheader1.c
./eternity2 -gen 8 21 204 eternity | grep ^int > genheader2.c
./eternity2 -gen 8 21 204 eternity | awk '/^POS/ { p=1 } p { print }' > gensearch.c
emcc -s EXPORTED_FUNCTIONS="['_main','_origmain']" -O2 -o eternity.js eternitygen.c
gcc -O6 -o eternity eternitygen.c
