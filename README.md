# eternity2
A program for solving Eternity II style puzzles using OpenCL

There's a Yahoo group for discussing this puzzle:

https://groups.yahoo.com/neo/groups/eternity_two

Here are some example uses of this program and what they do.

```
./eternity2 -cl b6x6s2 10
```

This solves a 6x6 puzzle using the GPU. There should be 40
solutions. This isn't very efficient, but it breaks the problem up
into 21894 smaller problems and assigns them to individual work
items. It's a good test because it doesn't take long to run but it
gives lots of work to the GPU.

```
./eternity2 -cl -cpu -maxwgs 8 -limit 200000 b10x10s1 10 1407888 26
```

This processes part of a very difficult 10x10 puzzle. You can replace
1407888 with any number from 0 to 4318955. Depending on the speed of
your hardware, this may take a few hours to complete.

```
./eternity2 -cl -limit 2000 b10x10s1 10 1407888 26
```

This does the same thing but uses the GPU instead of the CPU.

There's a newer Python version of the program in the python folder
which is more efficient, but not as configurable from the command
line.
