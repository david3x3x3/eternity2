This version of the solver is starting to get a lot faster than the C
version. There are a few performance improvements that make this
possible.

First of all, the workers use atomic_inc() to grab a new search
position when they finish searching the assigned position rather than
stopping and waiting for the host to assign them one on the next
kernel call.

Second, we automatically adjust the maximum number of nodes processed
per worker per kernel call. Once the number of search positions left
to search falls below the number of workers (workgroup size * compute
units), the GPU is able to process more nodes per second. Increasing
the node limit at the end of the run minimizes the number of kernel
calls and the associated overhead of lots of short kernel runs.

Here's an example of parameters to use:

  python solve.py pieces_set_2/pieces_07x07.txt 8 9

This solves Brendan's 7x7 puzzle. It starts with 8 nodes per kernel
call, but this is quickly adjusted upwards. The "9" means to search
the puzzle to depth 9 in the Python code to come up with the 98418
search positions to pass to the workers. On my NVIDIA GeForce RTX 3060
Laptop GPU, this finishes in about 33 seconds. The same search on the
same computer takes 3 minutes 14 seconds with the older OpenCL C code,
so the improvements are pretty big.

You can also search part of the puzzle in a single run (similar to the
C program). Here's an example:

  python solve.py pieces_set_1/pieces_10x10.txt 8 10 1407888 26
