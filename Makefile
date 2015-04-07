CC=gcc
CFLAGS=-O6 -Wall
CPPFLAGS=-I$(AMDAPPSDKROOT)/include

all: eternity2

eternity2: eternity2.o
	$(CC) $(CFLAGS) -o eternity2 eternity2.o -L$(AMDAPPSDKROOT)/lib/x86_64 -lOpenCL

clean:
	rm -fv *.o *.exe eternity2
