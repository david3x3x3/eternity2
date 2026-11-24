# Tuning solve.py for a GPU

The kernel's speed depends heavily on how many work groups run on each compute
unit and how many workers (threads) each group has. Each worker keeps its search
stack in local (shared) memory (`width*height*2` bytes: 200 B for 10x10), so
these two settings decide how many workers fit on the GPU at once. The best
values differ between GPUs and puzzle sizes.

## Automatic: `--tune`

```
python solve.py --tune                      # or: solve.exe --tune
```

This benchmarks a range of configurations on this machine's GPU and saves the
fastest to `tuning.json` in the current directory. After that, normal runs from
the same directory pick it up automatically and print
`using tuned config from tuning.json: ...`.

`tuning-defaults.json` (shipped with solve.py, bundled into solve.exe) holds
results measured on known GPUs, keyed the same way. It's used when there's no
local `tuning.json` entry, so rentals of those GPU models need no tuning. To add
a GPU, copy its entry from a `tuning.json` into `tuning-defaults.json`.
Measured so far (10x10, 224 × 2 on all NVIDIA): RTX 4070 Laptop 14.9G nodes/s,
RTX 3080 21.7G nodes/s, RTX 4070 SUPER 24.6G nodes/s, RTX 4080 34.2G nodes/s.
AMD Navi 10 (`gfx1010:xnack-`, RX 5600 XT/5700/5700 XT): 192 × 3, 3.1G nodes/s
(default 256 × 2: 2.9G). An RDNA "compute unit" in OpenCL is a pair of CUs with
128 KB of local memory, and a group holds at most 256 workers, so 3 groups fit.
Check row 380392 gives exact node counts on it.

- By default it benchmarks the 10x10 puzzle on a median-size row (428132), which
  takes minutes to finish, so every trial measures steady-state speed. To tune
  for a different puzzle, pass `--puzzle` / `--partial` as for a normal run, e.g.
  `--tune --puzzle 08x08_1 --partial 1,0`. Results are stored per
  (device, puzzle).
- Each trial runs the solver for `--tune-seconds` (default 8) with
  `--time-limit`, which never reports to the web server. A full tune takes about
  5–10 minutes.
- Sweep: first a coarse grid (group size in steps of 64, 1–16 groups per
  compute unit, skipping configs that would need more than about 240 KB of local
  memory per compute unit, which is roughly what an H100 has), then finer steps
  around the best one. OpenCL doesn't report a compute unit's total local memory,
  so the sweep stops adding groups once throughput falls below both the previous
  count's and 80% of the best so far. The top 3 are run again and averaged, to guard against
  noise such as laptop thermal throttling.
- Select the GPU with `--platform` / `--device` as usual. Re-run `--tune` after
  a driver update or a kernel change.
- Plug laptops in, and don't use the GPU for anything else while tuning.

`tuning.json` looks like:

```json
{
 "NVIDIA GeForce RTX 4070 Laptop GPU|10x10_1": {
  "wgs": 224, "groups_per_cu": 2, "mnodes_per_s": 14844,
  "default_mnodes_per_s": 12793, "tuned": "2026-11-21T15:40:01"
 }
}
```

## CUDA (`--cuda`)

Under `--cuda` the default is one block per SM, as large as fits (10x10 on
RTX 30xx/40xx: 486 x 1). CUDA lets a block use about 99 KB of shared memory,
versus OpenCL's 48 KB per group, so one copy of the lookup tables leaves room
for 486 workers per SM instead of 448. `--tune --cuda` sweeps CUDA configs and
saves them under a separate key (`<device> (CUDA)|<puzzle>`). On an RTX 3070
it confirmed 486 x 1 at 15.0G nodes/s (OpenCL 224 x 2: 14.3G). On the RTX 4070
Laptop it's 16.1G vs 14.9G. Throughput rises with workers per SM right up to
the shared-memory limit.

## Manual

```
python solve.py --puzzle 10x10_1 --partial 10,428132 --wgs 160 --groups-per-cu 2 --time-limit 10
```

- `--wgs N`: workers per work group.
- `--groups-per-cu M`: work groups launched per compute unit.
- `--time-limit S`: stop after S seconds. Compare runs by `nodes / search_seconds`.
  Never reports.

Explicit `--wgs` / `--groups-per-cu` override `tuning.json` and
`tuning-defaults.json`. Without any of them, the default is 2 groups per
compute unit, each filling the per-group local memory limit (10x10 on NVIDIA:
224 × 2), and 1 group on CPUs.

What to look for:
- Throughput rises with more workers per compute unit until all the groups no
  longer fit in the compute unit's local memory together. Then it falls sharply,
  because groups run one after another instead of together. On an RTX 4070
  Laptop (about 100 KB per compute unit, 48 KB per group), the best 10x10
  config on a long row is 2 × 224 = 448 workers per compute unit (both groups
  just fit), and 8x8 (smaller stacks) is around 600.
- Too few workers leaves the GPU idle while threads wait on memory.
- Node counts and results never depend on these settings, only speed.

Example (RTX 4070 Laptop, 10x10, 2026-11-21): `--tune` picked 224 × 2 over the
default 184 × 2 (+16% in trials). On the full median row 428132 that's 107 s
instead of 123 s. Short benchmark rows favor fewer workers, because host-side
splitting costs more with more workers, so tune on a long row (the default).
