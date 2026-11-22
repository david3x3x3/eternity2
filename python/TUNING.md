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

## Manual

```
python solve.py --puzzle 10x10_1 --partial 10,428132 --wgs 160 --groups-per-cu 2 --time-limit 10
```

- `--wgs N`: workers per work group.
- `--groups-per-cu M`: work groups launched per compute unit.
- `--time-limit S`: stop after S seconds. Compare runs by `nodes / search_seconds`.
  Never reports.

Explicit `--wgs` / `--groups-per-cu` override `tuning.json`. Without either,
the default is 2 groups per compute unit, each sized to use about 40 KB of local
memory (1 group on CPUs).

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
