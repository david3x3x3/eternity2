This program should be run from the command line, and there are
various options that you can include when running. If you type
"solve.exe -h", you get this help message:

```
usage: solve.exe [-h] [--clinfo] [--platform PLATFORM] [--device DEVICE] [--maxcu MAXCU] [--puzzle PUZZLE]
                 [--partial PARTIAL] [--reporter REPORTER] [--noreport]

options:
  -h, --help           show this help message and exit
  --clinfo             print OpenCL information and exit
  --platform PLATFORM  OpenCL platform number
  --device DEVICE      OpenCL device number
  --maxcu MAXCU        max compute units
  --puzzle PUZZLE      puzzle name, e.g. 10x10_1
  --partial PARTIAL    specifying which part of a puzzle to search (e.g. 10,r) for rowsize 10, random row
  --reporter REPORTER  name or alias of person reporting result (may be public)
  --noreport           don't report the results
```

If you want to see what OpenCL platforms and devices are available,
you can type "solve.exe --clinfo". On my system, this is what I see:

```
Plaform 0: NVIDIA CUDA
  Device 0: NVIDIA GeForce RTX 4070 Laptop GPU (4)
Plaform 1: Intel(R) OpenCL Graphics
  Device 0: Intel(R) Iris(R) Xe Graphics (4)
Plaform 2: Intel(R) OpenCL
  Device 0: 12th Gen Intel(R) Core(TM) i7-12700H (2)
```

By default, the program uses platform 0 and device 0, but you can change those with the command line options.

To benchmark your computer, you can try running this command. It
should find 13 solutions within a few minutes using decent hardware.

```
solve.exe --puzzle 08x08_1 --partial 1,0 --noreport
```

What I've been using this for recently is to look for additional
solutions to the 10x10 puzzle. You could use the following command for
that:

```
solve.exe --puzzle 10x10_1 --partial 10,r --reporter "John Doe"
```

The "partial" option tells the code to first search for all solutions
to the puzzle that include only the first 10 pieces, then pick one of
those partial solutions and use it to find all solutions by filling in
the remaining pieces (if possible).

The "r" in the partial option picks a row assignment. When using the
10x10_1 puzzle, the program requests a row number from a web service
to coordinate the search between multiple computers. If the web service
is unavailable, it falls back to picking a random number.

The "reporter" number says what name to include when reporting the
results to the web. If you don't specify a reporter, it will be
reported as "anonymous". I'm also recording the hostname of the
computer because I have several computers, and I'd like to know which
results came from each. The web server also stores the IP address that
the results are submitted from.
