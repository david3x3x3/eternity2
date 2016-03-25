PROJ=eternity2

#CC=x86_64-w64-mingw32-gcc
CC=i686-pc-mingw32-gcc
#CC=gcc

CFLAGS=-std=c99 -DUNIX -O6 -Wall -DDEBUG -I"c:/Program Files (x86)/Intel/OpenCL SDK/5.3/include"

# Check for 32-bit vs 64-bit
#PROC_TYPE = $(strip $(shell uname -m | grep 64))
PROC_TYPE =

# Check for Mac OS
OS = $(shell uname -s 2>/dev/null | tr [:lower:] [:upper:])
DARWIN = $(strip $(findstring DARWIN, $(OS)))

# MacOS System
ifneq ($(DARWIN),)
	CFLAGS += -DMAC
	LIBS=-framework OpenCL

	ifeq ($(PROC_TYPE),)
		CFLAGS+=-arch i386
	else
		CFLAGS+=-arch x86_64
	endif
else

# Linux OS
LIBS=-lOpenCL
ifeq ($(PROC_TYPE),)
	CFLAGS+=-m32
else
	CFLAGS+=-m64
endif

# Check for Linux-AMD
ifdef AMDAPPSDKROOT
   INC_DIRS=. $(AMDAPPSDKROOT)/include
	ifeq ($(PROC_TYPE),)
		LIB_DIRS=$(AMDAPPSDKROOT)/lib/x86
	else
		LIB_DIRS=$(AMDAPPSDKROOT)/lib/x86_64
	endif
else

# Check for Linux-Nvidia
ifdef NVSDKCOMPUTE_ROOT
   INC_DIRS=. $(NVSDKCOMPUTE_ROOT)/OpenCL/common/inc
endif

endif
endif

$(PROJ): $(PROJ).c
	#$(CC) $(CFLAGS) -o $@ $^ $(INC_DIRS:%=-I%) $(LIB_DIRS:%=-L%) -L"c:/Program Files (x86)/Intel/OpenCL SDK/5.3/lib/x64" $(LIBS)
	#$(CC) $(CFLAGS) -o $@ $^ $(INC_DIRS:%=-I%) $(LIB_DIRS:%=-L%) -Lc:/windows/system32 $(LIBS)
	$(CC) $(CFLAGS) -o $@ $^ $(INC_DIRS:%=-I%) $(LIB_DIRS:%=-L%) -L"c:/Program Files (x86)/Intel/OpenCL SDK/5.3/lib/x86" $(LIBS)

.PHONY: clean

clean:
	rm $(PROJ)
