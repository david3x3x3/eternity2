# Running solve.py unattended (cloud GPUs, multi-GPU servers)

## Typical command

```
python solve.py --all-devices --puzzle 10x10_1 --partial 10,r --reporter <name> --max-hours 10
```

- `--partial 10,r`: get a row from the e2db web service (puzzlingaddiction.com),
  search it, report the result, repeat. If the service can't be reached, it
  picks a random row instead. With `--noreport` it never contacts the service
  and always picks random rows.
- `--all-devices`: one solver per GPU of the OpenCL platform (`--platform`,
  default 0). Each child writes `gpu<N>.log` and reports hostname `<host>/gpu<N>`.
  Stopping the parent (Ctrl+C, or SIGTERM, e.g. `docker stop`) stops all
  children. They also die if the parent is killed outright (a job object on
  Windows, the parent-death signal on Linux).
- `--max-hours H`: don't start a new row after H hours. The current row
  finishes and is reported, then the process exits, so stopping takes up to
  one row's runtime past H. A process that's killed mid-row loses that row's
  work only. The server locks assigned rows for 7 days, then hands them out
  again.
- `--reporter <name>`: the name stored with results (default `anonymous`).

## Credentials

The reporter password comes from the `E2DB_PASSWORD` environment variable if
it's set, otherwise from `password.txt` next to solve.py. For cloud images, set
it as an environment variable in the template rather than baking
`password.txt` into an image or repo.

## Data files

- `10x10-10-rowindex.txt` (4 KB, in the repo): maps a 10x10 row id to its
  starting position in about 0.25 s. The 650 MB `10x10-10-cached.txt` is no
  longer needed (it's still used if present and the index isn't). To build an
  index for another puzzle: `python solve.py --puzzle <name> --make-row-index`.
- `pieces_set_1/`: puzzle definitions.
- `tuning.json`: per-device work-group config written by `--tune`
  (see TUNING.md). Tune once per GPU model with `--device N`; `--all-devices`
  children use it automatically.

## First session on new hardware

1. `python solve.py --tune` (5–15 min): finds this GPU's best config and prints
   its nodes/s. Multi-GPU: tune on one device while the others are idle.
2. `python solve.py --puzzle 10x10_1 --partial 10,380392 --noreport`: must
   report `nodes = 114933467966` and `best = 88`.
3. The typical command above for the rest of the rental.

## Docker notes

- The NVIDIA container runtime provides the OpenCL library when the `compute`
  capability is enabled (`NVIDIA_DRIVER_CAPABILITIES=compute,utility`). The
  image also needs `/etc/OpenCL/vendors/nvidia.icd` containing
  `libnvidia-opencl.so.1`.
- Python packages: `pip install -r requirements.txt` (numpy, pyopencl,
  requests, pytz).
