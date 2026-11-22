#!/usr/bin/env python
import sys
import pyopencl as cl
import numpy as np
import time
import os
import random
import re
import argparse
import requests
import socket
import subprocess
import bisect
from datetime import datetime, timezone
import json
from requests.auth import HTTPDigestAuth

print('args = %s' % ' '.join(sys.argv))

#os.environ['PYOPENCL_COMPILER_OUTPUT'] = '1'     # rather cool but important for CodeXL
#os.environ['PYOPENCL_NO_CACHE'] = '1'            # obsoletes relics which can negatively impact CodeXL

def pos_to_str(p):
    res = ''
    for p0 in p:
        if fit2[p0]:
            res += f'{fit2[p0][0]+1}/{fit2[p0][1]} '
        else:
            res += f'({p0}) '
    return res

def print_pos(p):
    print(pos_to_str(p), flush=True)

def fit_check(placed, add_padding):
    if add_padding:
        placed[0:0] = [dummypos]*width
    up=pieces[fit2[placed[-width]]][2]
    left=pieces[fit2[placed[-1]]][1]
    right = int(len(placed) % width == width - 1)
    down = int(len(placed) // width == height)
    placed += [fit1[((left*edgecount+up)*2+down)*2+right]-1]
    if add_padding:
        del placed[:width]

do_trace = False

def deepen(orig_pos, src, pos_list, src_list, old_depth, debug):
    pos = list(orig_pos)
    # if len(pos) < old_depth:
    #     debug = True
    # if len(pos) > 0 and len(pos) == old_depth + 1 and fit2[pos[-1]]:
    #     debug = True
    if debug:
        print(f'deepen(poslen={len(pos)}, pos={pos_to_str(pos)}, old_depth={old_depth})')
        print(f'src = {src}')
    if len(pos) <= old_depth:
        return 0
    nodes = 0
    if len(pos) > 0 and len(pos) == old_depth + 1 and not fit2[pos[-1]]:
        del pos[-1]
    partial = []
    if len(pos) > old_depth:
        partial = list(pos)
        del pos[old_depth:]
        if len(partial) > old_depth+1:
            pos_list += [partial]
            if do_trace:
                src_list += [src + pos_to_str(partial) + '\n']
        if debug:
            print(f' trimmed pos = {pos_to_str(pos)}')
    pos1 = [dummypos]*width + pos
    up=pieces[fit2[pos1[-width]]][2]
    left=pieces[fit2[pos1[-1]]][1]
    right = int(len(pos1) % width == width - 1)
    down = int(len(pos1) // width == height)
    if debug:
        print(f' urdl = {up}, {right}, {down}, {left}')
    used = set([fit2[p][0] for p in pos if fit2[p]])
    p = fit1[((left*edgecount+up)*2+down)*2+right]
    while fit2[p]:
        if debug:
            print(f' {pos_to_str(pos + [p])}')
        pos2 = pos + [p]
        fit_check(pos2, True)
        if fit2[p][0] not in used:
            if pos2 > partial and (len(partial) >= len(pos2) or pos + [p] > partial):
                if debug:
                    print(f'pos2 = {pos_to_str(pos2)}')
                    print(f'partial = {pos_to_str(partial)}')
                    print(f'pos + [p] = {pos_to_str(pos + [p])}')
                # count node for adding a piece even if it's trimmed due to lack of extension
                nodes += 1
                if pos2[-1] != 0:
                    if debug:
                        print('  adding position')
                    pos_list += [pos2]
                    if do_trace:
                        src_list += [src + pos_to_str(pos2) + '\n']
                    if pos2 == partial:
                        print('this should never happen')
                        sys.exit(0)
                else:
                    if debug:
                        print('  no extensions beyond position')
            else:
                if debug:
                    print('  position already searched')
        else:
            if debug:
                print('  piece used more than once')
        p += 1
    return nodes

def deepen_list(pos_list, src_list, pos_list2, src_list2, old_depth, debug):
    last_status = 0
    if debug:
        print(f'DEEPEN_LIST {[pos_to_str(p) for p in pos_list]}')
        list_check = set(map(tuple, pos_list))
        if len(list_check) != len(pos_list):
            print('COMPLETE DUPS IN LIST!')
            for i, p in enumerate(pos_list):
                for p2 in pos_list[i+1:]:
                    if p == p2:
                        print(f' {pos_to_str(p)}')
    nodes = 0
    for i, pos in enumerate(pos_list):
        if nodes - last_status >= 2000000:
            print(f'checking {pos_to_str(pos)}', flush=True)
            last_status = nodes
        nodes += deepen(pos, src_list[i] if do_trace else [], pos_list2, src_list2, old_depth, debug)
    return nodes

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_password():
    """Reporter password: $E2DB_PASSWORD if set, else password.txt."""
    if os.environ.get('E2DB_PASSWORD'):
        return os.environ['E2DB_PASSWORD']
    with open(resource_path('password.txt'), 'r') as fp:
        return fp.readlines()[0].strip()

def request_row():
    try:
        auth_object = HTTPDigestAuth('reporter', get_password())
        url = "https://puzzlingaddiction.com/e2db/request_row"
        try:
            response = requests.get(url, auth=auth_object, timeout=10)
        except requests.exceptions.Timeout:
            print('request_row failed: request timed out', flush=True)
            return None
        except requests.exceptions.RequestException as e:
            print(f'request_row failed: {e}', flush=True)
            return None
        if not response.ok:
            print(f'request_row failed: HTTP {response.status_code}', flush=True)
            return None
        try:
            return response.json()['row_num']
        except (ValueError, KeyError) as e:
            print(f'request_row failed: invalid response - {e}', flush=True)
            return None
    except Exception as e:
        print(f'request_row failed: {e}', flush=True)
        return None

ROW_INDEX_PREFIX = 3   # cells per prefix in the row index

def row_index_file(puzzname, width):
    return resource_path(f'{puzzname}-{width}-rowindex.txt')

def top_rows(prefix=()):
    """Yield every valid top row starting with `prefix` (fit2 indices), in row-id
    order, as a position in the row cache's format: the row's fit2 indices plus
    the 'one before the first candidate' index of the next cell. Positions whose
    next cell has no candidates are skipped, as when the cache was built."""
    used = {fit2[p][0] for p in prefix}
    def rec(pos):
        tail = list(pos)
        fit_check(tail, True)
        if tail[-1] == 0:
            return
        if len(pos) == width:
            yield tail
            return
        p = tail[-1] + 1
        while fit2[p]:
            if fit2[p][0] not in used:
                used.add(fit2[p][0])
                yield from rec(pos + [p])
                used.discard(fit2[p][0])
            p += 1
    yield from rec(list(prefix))

def make_row_index(fn):
    """Write the first row id of every ROW_INDEX_PREFIX-cell prefix, plus the total."""
    entries, last, n = [], None, 0
    for n, pos in enumerate(top_rows()):
        if pos[:ROW_INDEX_PREFIX] != last:
            last = pos[:ROW_INDEX_PREFIX]
            entries.append((n, last))
    with open(fn, 'w', newline='\n') as fp:
        fp.write(f'total {n + 1}\n')
        for first, prefix in entries:
            fp.write(f'{first} {",".join(map(str, prefix))}\n')
    print(f'wrote {fn}: {n + 1} rows, {len(entries)} prefixes')

def load_row_index(fn):
    with open(fn) as fp:
        total = int(fp.readline().split()[1])
        entries = [(int(a), tuple(map(int, b.split(',')))) for a, b in (l.split() for l in fp if l.strip())]
    return total, entries

def row_position(index, row_num):
    """Position (row cache format) of top row `row_num`, via the prefix index."""
    total, entries = index
    if not 0 <= row_num < total:
        sys.exit(f'row {row_num} out of range (0..{total - 1})')
    k = bisect.bisect_right([e[0] for e in entries], row_num) - 1
    first, prefix = entries[k]
    for n, pos in enumerate(top_rows(prefix), first):
        if n == row_num:
            return pos

def run_all_devices(platform):
    """Run one child solver per device of `platform`; stop them all when this process stops."""
    exe = [sys.executable] if getattr(sys, 'frozen', False) else [sys.executable, os.path.abspath(sys.argv[0])]
    argv, skip = [], False
    for a in sys.argv[1:]:                      # drop --all-devices and any --device N
        if skip:
            skip = False
        elif a == '--all-devices':
            pass
        elif a == '--device':
            skip = True
        elif not a.startswith('--device='):
            argv.append(a)
    devices = platform.get_devices()
    kill_on_parent_exit = None
    if sys.platform == 'win32':
        # a job object kills the children if this process dies, even if it's killed outright
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        job = k32.CreateJobObjectW(None, None)
        class LIMITS(ctypes.Structure):
            _fields_ = [('PerProcessUserTimeLimit', ctypes.c_int64), ('PerJobUserTimeLimit', ctypes.c_int64),
                        ('LimitFlags', wintypes.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t),
                        ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', wintypes.DWORD),
                        ('Affinity', ctypes.c_size_t), ('PriorityClass', wintypes.DWORD),
                        ('SchedulingClass', wintypes.DWORD)]
        class EXT_LIMITS(ctypes.Structure):
            _fields_ = [('BasicLimitInformation', LIMITS), ('IoInfo', ctypes.c_uint64 * 6),
                        ('ProcessMemoryLimit', ctypes.c_size_t), ('JobMemoryLimit', ctypes.c_size_t),
                        ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]
        info = EXT_LIMITS()
        info.BasicLimitInformation.LimitFlags = 0x2000   # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))
    else:
        # Linux: the kernel sends SIGTERM to the child when this process dies
        import ctypes, signal
        libc = ctypes.CDLL(None)
        def kill_on_parent_exit():
            libc.prctl(1, signal.SIGTERM)          # PR_SET_PDEATHSIG
        # docker stop / kill send SIGTERM: turn it into KeyboardInterrupt for cleanup below
        def on_term(signum, frame):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, on_term)
    children = []
    try:
        for i in range(len(devices)):
            log = open(f'gpu{i}.log', 'a')
            cmd = exe + argv + ['--device', str(i), '--hostname-suffix', f'/gpu{i}']
            p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, preexec_fn=kill_on_parent_exit)
            if sys.platform == 'win32':
                k32.AssignProcessToJobObject(job, int(p._handle))
            children.append((p, log))
            print(f'device {i} ({devices[i].name.strip()}): pid {p.pid}, log gpu{i}.log', flush=True)
        for p, log in children:
            p.wait()
    except KeyboardInterrupt:
        print('stopping children', flush=True)
        for p, log in children:
            p.terminate()
        for p, log in children:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
    finally:
        for p, log in children:
            log.close()
    return max((p.returncode or 0) for p, log in children) if children else 0

TUNING_FILE = 'tuning.json'
TUNING_DEFAULTS = 'tuning-defaults.json'   # shipped with solve.py: results measured on known GPUs

def load_tuning(fn=TUNING_FILE):
    try:
        with open(fn) as fp:
            return json.load(fp)
    except (OSError, ValueError):
        return {}

def tuning_key(device, puzzle):
    return f'{device.name.strip()}|{puzzle}'

def run_trial(base_args, wgs, groups_per_cu, seconds):
    """Run this solver for `seconds` with one work-group config; return nodes/s (0 on failure)."""
    exe = [sys.executable] if getattr(sys, 'frozen', False) else [sys.executable, os.path.abspath(sys.argv[0])]
    cmd = exe + base_args + ['--wgs', str(wgs), '--groups-per-cu', str(groups_per_cu),
                             '--time-limit', str(seconds), '--noreport']
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    nodes = re.search(r'^nodes = (\d+)$', out, re.M)
    secs = re.search(r'^search_seconds = ([\d.]+)$', out, re.M)
    return int(nodes.group(1)) / float(secs.group(1)) if nodes and secs else 0.0

def tune(args, device, static_local, width, height, default_cfg):
    """Benchmark work-group configs on this device and save the fastest to TUNING_FILE."""
    per_worker = width*height*2
    max_wgs = min(device.max_work_group_size, (device.local_mem_size - static_local)//per_worker)
    # OpenCL only reports the per-group limit, not a compute unit's total local
    # memory (RTX 40xx: ~100 KB, A100 ~164 KB, H100 ~228 KB). Try configs up to
    # ~240 KB per compute unit, and stop adding groups once throughput drops.
    cap = 240*1024
    def fits(w, g):
        return 0 < w <= max_wgs and g*(w*per_worker + static_local) <= cap
    base_args = ['--platform', str(args.platform), '--device', str(args.device),
                 '--puzzle', args.puzzle, '--partial', args.partial]
    if args.maxcu:
        base_args += ['--maxcu', str(args.maxcu)]
    results = {}
    def trial(w, g):
        if (w, g) not in results and fits(w, g):
            rate = run_trial(base_args, w, g, args.tune_seconds)
            results[(w, g)] = [rate]
            print(f'  wgs={w:4d} groups_per_cu={g}: {rate/1e6:8.0f} M nodes/s', flush=True)

    print(f'tuning {device.name.strip()} on {args.puzzle} --partial {args.partial}, '
          f'{args.tune_seconds} s per trial', flush=True)
    trial(*default_cfg)
    best_by_g = {}
    for g in range(1, 17):                      # coarse pass
        for w in sorted(set(list(range(64, max_wgs+1, 64)) + [max_wgs])):
            trial(w, g)
        rates = [results[(w, g2)][0] for (w, g2) in results if g2 == g]
        if not rates:
            break
        best_by_g[g] = max(rates)
        overall = max(best_by_g.values())
        if g >= 3 and best_by_g[g] < best_by_g[g-1] and best_by_g[g] < 0.8*overall:
            break                               # more groups no longer fit or help
    w0, g0 = max(results, key=lambda k: results[k][0])
    for dw in (-48, -32, -16, 16, 32, 48):      # refine around the best
        trial(w0 + dw, g0)
    # re-run the top 3 to guard against noise (e.g. laptop thermal throttling)
    top = sorted(results, key=lambda k: -results[k][0])[:3]
    print('confirming top configs:', flush=True)
    for k in top:
        results[k].append(run_trial(base_args, k[0], k[1], args.tune_seconds))
        print(f'  wgs={k[0]:4d} groups_per_cu={k[1]}: {results[k][-1]/1e6:8.0f} M nodes/s', flush=True)
    best_cfg = max(top, key=lambda k: sum(results[k])/len(results[k]))
    rate = sum(results[best_cfg])/len(results[best_cfg])
    default_rate = results.get(tuple(default_cfg), [0])[0]
    tuning = load_tuning()
    tuning[tuning_key(device, args.puzzle)] = {
        'wgs': best_cfg[0], 'groups_per_cu': best_cfg[1], 'mnodes_per_s': round(rate/1e6),
        'default_mnodes_per_s': round(default_rate/1e6), 'tuned': datetime.now().isoformat(timespec='seconds')}
    with open(TUNING_FILE, 'w') as fp:
        json.dump(tuning, fp, indent=1)
    print(f'best: --wgs {best_cfg[0]} --groups-per-cu {best_cfg[1]} ({rate/1e6:.0f} M nodes/s; '
          f'default {default_cfg[0]}x{default_cfg[1]}: {default_rate/1e6:.0f} M nodes/s)')
    print(f'saved to {os.path.abspath(TUNING_FILE)}')

if __name__ == '__main__':
    if len(sys.argv) == 1:
        if sys.platform == 'win32':
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
        from solve_gui import SolveApp
        SolveApp().run()
        sys.exit(0)

    parser = argparse.ArgumentParser()
    parser.add_argument("--clinfo", help="print OpenCL information and exit", action="store_true")
    parser.add_argument("--platform", help="OpenCL platform number", type=int, default=0)
    parser.add_argument("--device", help="OpenCL device number", type=int, default=0)
    parser.add_argument("--maxcu", help="max compute units", type=int)
    parser.add_argument("--wgs", help="work-group size (default: as many as fit in local memory)", type=int)
    parser.add_argument("--groups-per-cu", help="work groups launched per compute unit (default: 2 on GPUs)", type=int)
    parser.add_argument("--puzzle", help="puzzle name, e.g. 10x10_1", type=str)
    parser.add_argument("--partial", help="specifying which part of a puzzle to search (e.g. 10,r) for rowsize 10, random row", type=str)
    parser.add_argument("--reporter", help="name or alias of person reporting result (may be public)", type=str)
    parser.add_argument("--noreport", help="don't report the results", action="store_true")
    parser.add_argument("--time-limit", help="stop the search after this many seconds (benchmarking; never reports)", type=float)
    parser.add_argument("--tune", help=f"benchmark work-group configs for this device and puzzle, save the best to {TUNING_FILE}", action="store_true")
    parser.add_argument("--dump-ptx", help="write the compiled kernel (PTX on NVIDIA) to this file and exit", type=str)
    parser.add_argument("--depth-stats", help="count nodes per board cell (slower; for analysis)", action="store_true")
    parser.add_argument("--max-hours", help="with a random/assigned row (10,r): don't start new rows after this many hours", type=float)
    parser.add_argument("--all-devices", help="run one solver per device of the platform (logs: gpu<N>.log); stopping this process stops them", action="store_true")
    parser.add_argument("--hostname-suffix", help=argparse.SUPPRESS, default='')
    parser.add_argument("--make-row-index", help="write the top-row index for --puzzle (lets --partial W,N run without the row cache)", action="store_true")
    parser.add_argument("--tune-seconds", help="seconds per tuning trial (default 8)", type=float, default=8)

    args = parser.parse_args()
    if args.time_limit:
        args.noreport = True
    if args.tune:
        # default benchmark: a median-size 10x10 row that runs much longer than a trial
        args.puzzle = args.puzzle or '10x10_1'
        args.partial = args.partial or '10,428132'
    for i in range(len(cl.get_platforms())):
        p = cl.get_platforms()[i]
        print('Plaform ' + str(i) + ': ' + p.name)
        for j in range(len(p.get_devices())):
            d = p.get_devices()[j]
            print('  Device ' + str(j) + ': ' + str(d.name) + ' (' + str(d.type) + ')')

    platform = cl.get_platforms()[args.platform]
    if args.all_devices:
        if args.tune:
            sys.exit('--tune runs on one device; use --device N')
        sys.exit(run_all_devices(platform))
    device = platform.get_devices()[args.device]
    program_start = time.time()

    print(platform)
    print("===============================================================")
    print("Platform name:", platform.name)
    print("Platform profile:", platform.profile)
    print("Platform vendor:", platform.vendor)
    print("Platform version:", platform.version)

    print(device)
    print("---------------------------------------------------------------")
    print("Device name:", device.name)
    print("Device type:", cl.device_type.to_string(device.type))
    print("Device memory: ", device.global_mem_size//1024//1024, 'MB')
    print("Device local memory: ", device.local_mem_size, 'B')
    print("Device max clock speed:", device.max_clock_frequency, 'MHz')
    print("Device compute units:", device.max_compute_units)
    print("Device max work group size:", device.max_work_group_size)
    print("Device max work item sizes:", device.max_work_item_sizes)

    if args.clinfo:
        sys.exit(0)

    ctx = cl.Context([device])
    print('ctx = {}'.format(ctx))
    queue = cl.CommandQueue(ctx)
    print('queue = {}'.format(queue))

    edgecount = 0

    #print('reading piece data')
    # read the piece definition file
    puzzname = args.puzzle.split('_')[0]
    puzzset = args.puzzle.split('_')[1]
    random_partial = False
    fn = f'pieces_set_{puzzset}/pieces_{puzzname}.txt'
    fp=open(resource_path(fn),'r')
    width, height = list(map(int,fp.readline().strip('\n').split(' ')))
    pieces = dict()
    piecenum=0
    pypieces = ''
    for line in fp.read().splitlines():
        t1 = tuple(map(int,line.split(' ')))
        pypieces += '{'+','.join(map(str,t1))+'},'
        if max(t1) >= edgecount:
            edgecount = max(t1) + 1
        for rot in range(4):
            pieces[(piecenum,rot)] = t1[-rot:] + t1[:-rot]
        piecenum += 1
    #print('pypieces = ' + str(pypieces))
    print('edgecount = ' + str(edgecount))
    fp.close()
    # kernel limits: 128-bit used-piece mask; packed candidate entries hold an
    # 8-bit piece number and color*edgecount*4 in 12 bits
    if piecenum > 128 or edgecount > 32:
        sys.exit(f'kernel supports at most 128 pieces and 32 colors (got {piecenum}, {edgecount})')

    fit = dict()
    for key1, val in pieces.items():
        # if val[0] == 0 and val[3] == 0 and key1[0] != 0:
        #     # only try one corner in top left
        #     # continue

        #     # Only testing with the first corner at the top is good for
        #     # small puzzles, but for larger puzzles I'm trying to get
        #     # better first rows that may not start with the first
        #     # corner. Maybe this should be a command line or config file
        #     # option in the future.
        #     pass
        key2 = (val[0], val[3], val[1] == 0, val[2] == 0)
        if not fit.get(key2):
            fit[key2] = []
        fit[key2] += [key1]

    fit1 = [1]*edgecount*edgecount*4
    fit2 = [None]*3
    fit2c = ["{-1,0}"]*3
    dummypos = -10

    # We could randomize here as a quick way to pick random positions, but
    # it's better to use command line args.
    # for f in sorted(fit):
    #    random.shuffle(fit[f])

    # print(f'fit = {fit}')
    for f in sorted(fit):
        # print('f = ' + str(f))
        # print('  ' + str(fit[f]))
        f3 = ['{'+str(f2[0])+','+str(f2[1])+'}' for f2 in fit[f]]
        # left, up, down, right
        pos = ((f[1]*edgecount+f[0])*2+f[3])*2+f[2]
        if f[2] and f[3]:
            dummypos = len(fit2)
        if len(f3) > 0:
            fit1[pos] = len(fit2)
            fit2 = fit2 + fit[f] + [None]
            fit2c = fit2c + f3 + ['{-1,0}']
        else:
            fit1[pos] = 2

    if args.make_row_index:
        make_row_index(row_index_file(puzzname, width))
        sys.exit(0)

    fp = open(resource_path('eternity2_kernel.cl'),'r')
    prgsrc = fp.read()
    fp.close()

    # print('fit1 =', fit1)
    # print('fit2 =', fit2)
    # print('fit2c =', fit2c)
    prgsrc = prgsrc.replace('KMEMTYPE','local')
    if args.depth_stats:
        prgsrc = '#define DEPTH_STATS\n' + prgsrc
    prgsrc = prgsrc.replace('KGLOBMEM','0')
    prgsrc = prgsrc.replace('PYPIECES',pypieces)
    prgsrc = prgsrc.replace('PYFITTABLE1',','.join(map(str,fit1)))
    prgsrc = prgsrc.replace('PYFITTABLE2',','.join(map(str,fit2c)))
    prgsrc = prgsrc.replace('PYEDGECOUNT',str(edgecount))
    prgsrc = prgsrc.replace('KWIDTH',str(width))
    prgsrc = prgsrc.replace('KHEIGHT',str(height))

    # print('src = ' + prgsrc)
    prog = cl.Program(ctx, prgsrc).build()
    kernel = prog.mykernel
    if args.dump_ptx:
        with open(args.dump_ptx, 'wb') as fp:
            fp.write(prog.binaries[0])
        print(f'wrote {args.dump_ptx}')
        sys.exit(0)
    #print(kernel)

    static_local = kernel.get_work_group_info(cl.kernel_work_group_info.LOCAL_MEM_SIZE, device)
    print('kernel.LOCAL_MEM_SIZE = ' + str(static_local))

    # print(f'fit1 (len {len(fit1)}) = ' + str(fit1))
    # print(f'fit2 (len {len(fit2)}) = ' + str(fit2))

    maxcu = device.max_compute_units
    # Work-group sizing. Each worker needs width*height*2 bytes of local memory,
    # and the kernel's static local memory (lookup tables) comes out of each
    # group's budget too. On GPUs, 2 groups per compute unit, each filling the
    # group limit, measured best for 10x10 on an RTX 4070 Laptop and an RTX 3080
    # (--tune; docs/ROADMAP.md).
    is_gpu = device.type == cl.device_type.GPU
    groups_per_cu = args.groups_per_cu or (2 if is_gpu else 1)
    group_local = device.local_mem_size
    wgs = (group_local - static_local)//(width*height*2)
    if not is_gpu:
        wgs = 1
    if device.max_work_group_size < wgs:
        wgs = device.max_work_group_size
    if args.tune:
        tune(args, device, static_local, width, height, (wgs, groups_per_cu))
        sys.exit(0)
    key = tuning_key(device, args.puzzle)
    for fn in (TUNING_FILE, resource_path(TUNING_DEFAULTS)):
        tuned = load_tuning(fn).get(key)
        if tuned and not (args.wgs or args.groups_per_cu):
            wgs, groups_per_cu = tuned['wgs'], tuned['groups_per_cu']
            print(f'using tuned config from {os.path.basename(fn)}: wgs={wgs}, groups_per_cu={groups_per_cu}')
            break
    if args.wgs:
        wgs = args.wgs
    print('wgs = ' + str(wgs))
    cu = device.max_compute_units
    if args.maxcu:
        cu = min(cu, args.maxcu)
    # cu is used below as "number of work groups"
    cu *= groups_per_cu
    print('cu = ' + str(cu))
    lm = cl.LocalMemory(wgs*(width*height*2))
    print('total workers = %d' % (wgs*cu))

    while True:
        # which pieces are in each location. we put a row of blank pieces at
        # the top so that we can always match the piece above the current one,
        # even in the top row.
        placed = [dummypos]*width+[2]
        nodes1 = 0
        nodes = 0
        i = 0
        node_limit = 16
        print('node limit = ' + str(node_limit))

        search_args = args.partial.split(',') if args.partial else []
        print('search_args = %s' % search_args)
        if len(search_args) <= i:
            # default to searching the whole puzzle
            search_args += [0, 0]

        limit=int(search_args[i])
        i += 1

        print('depth limit = ' + str(limit))

        start_time = int(time.time())

        pos = []
        fit_check(pos, True)
        pos_list = [pos]
        src_list = [""]
        depth=0
        arg_shortcut = False
        prev_pct = 1.0
        while True:
            if depth == 0:
                fn = f'{puzzname}-{limit}-cached.txt'
                index_fn = row_index_file(puzzname, limit)
                if limit == width and i+1 == len(search_args) and os.path.exists(index_fn):
                    # one top row: look it up in the small row index (no row cache needed)
                    index = load_row_index(index_fn)
                    if search_args[i] == 'r':
                        random_partial = True
                        j = None
                        if not args.noreport and puzzname == '10x10' and limit == 10:
                            j = request_row()
                        if j is None:
                            j = random.randrange(index[0])
                            print(f'row_num = {j} (randomly assigned)', flush=True)
                        else:
                            print(f'row_num = {j} (assigned by web service)', flush=True)
                        search_args[i] = str(j)
                    pos_list = [row_position(index, int(search_args[i]))]
                    print(f'row {search_args[i]} from {os.path.basename(index_fn)}')
                    depth = limit
                    arg_shortcut = True
                elif os.path.exists(fn):
                    depth = limit
                    with open(fn, 'r') as fp:
                        pos_list = []
                        print(f'reading stored row data')
                        print(f'search_args = {search_args}, i = {i}')
                        if i+1 == len(search_args):
                            # just pick one row
                            if search_args[i] == 'r':
                                random_partial = True
                                if fn == '10x10-10-cached.txt':
                                    j = None
                                    if not args.noreport:
                                        j = request_row()
                                    if j is None:
                                        j = random.randrange(19864204)
                                        print(f'row_num = {j} (randomly assigned)', flush=True)
                                    else:
                                        print(f'row_num = {j} (assigned by web service)', flush=True)
                                    search_args[i] = str(j)
                                    while j >= 0:
                                        line = fp.readline()
                                        j -= 1
                                else:
                                    #this probably defeats my goals of not reading lots of stuff into memory
                                    lines = fp.readlines()
                                    j = random.randrange(len(lines))
                                    search_args[i] = str(j)
                                    line = lines[j]
                            else:
                                for j, line in enumerate(fp):
                                    if j == int(search_args[i]):
                                        break
                            pos_list = [list(map(int,line.strip().split(',')))]
                            arg_shortcut = True
                        else:
                            lines = fp.readlines()
                            for linenum, line in enumerate(lines):
                                if linenum % 1000000 == 0:
                                    print(f'line {linenum}', flush=True)
                                elif linenum % 100000 == 0:
                                    print(f'.', end='', flush=True)
                                pos_list += [list(map(int,line.strip().split(',')))]
                else:
                    while depth < limit:
                        pos_list2 = []
                        src_list2 = []
                        nodes1 += deepen_list(pos_list, src_list, pos_list2, src_list2, depth, False)
                        pos_list = pos_list2
                        src_list = src_list2
                        depth += 1
                        print(f'{len(pos_list)} positions at depth {depth}, nodes = {nodes1}', flush=True)
                    print('saving row search for future runs')
                    if len(pos_list) >= 1000000:
                        with open(fn, 'w') as fp:
                            for p in pos_list:
                                fp.write(','.join(map(str,p)) + '\n')
            if arg_shortcut == True:
                break
            print("%d positions found with depth %d" % (len(pos_list), depth))
            if len(search_args) > i:
                print(f'search_args[{i}] == {search_args[i]}')
                depth = limit
                if search_args[i] == 'r':
                    random_partial = True
                    j = None
                    if not args.noreport and args.puzzle == '10x10_1' and args.partial == '10,r':
                        j = request_row()
                    if j is None:
                        j = random.randrange(len(pos_list))
                        print(f'row_num = {j} (randomly assigned)', flush=True)
                    else:
                        print(f'row_num = {j} (assigned by web service)', flush=True)
                    search_args[i] = str(j)
                else:
                    j = int(search_args[i])
                pos_list = [pos_list[j],]
                print(f'searching ', end='')
                print_pos(pos_list[0])
                placed = [dummypos]*width + pos_list[0]
                i += 1
                if len(search_args) > i:
                    limit = int(search_args[i])
                    i += 1
                    pos_list = []
                else:
                    break
            # break # gotta fix nested --partial arguments

        row_num = int(search_args[-1])

        # try to figure out how far to extend the search to get 10x the number of positions as workers
        while len(pos_list) < wgs*cu*2:
            pos_list2 = []
            src_list2 = []
            nodes += deepen_list(pos_list, src_list, pos_list2, src_list2, limit, False)
            pos_list = pos_list2
            src_list = src_list2
            limit += 1
            # print(f'pos_list = {pos_list}')
            print(f'{len(pos_list)} positions after extending to depth {limit}', flush=True)
        #print('{}: pos_list = {}'.format(len(pos_list), pos_list))

        print('modified args = %s' % search_args)

        def list_to_np(pl):
            piece_data = np.full((len(pl), width*height), -1, np.int16)
            for i, pos in enumerate(pl):
                k = min(len(pos), width*height)
                piece_data[i, :k] = pos[:k]
            return piece_data.ravel()

        piece_data = list_to_np(pos_list)

        nassign_data = np.array([1], np.int32)

        worker_pos = np.array([0]*wgs*cu, np.int32)
        for i in range(wgs*cu):
            if i > len(pos_list):
                worker_pos[i] = -1
            else:
                worker_pos[i] = i
                nassign_data[0] = i+1

        nassign_buffer = cl.Buffer(ctx,
                                  cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR,
                                  hostbuf=nassign_data)

        piece_buffer = cl.Buffer(ctx,
                                 cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR,
                                 hostbuf=piece_data)

        worker_buffer = cl.Buffer(ctx,
                                  cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR,
                                  hostbuf=worker_pos)

        # len(pos_list) is just a guess at the max results per kernel run
        #found_limit = 1000
        found_limit = 200
        found_data = np.array([0]*width*height*found_limit, np.int16)
        found_buffer = cl.Buffer(ctx, cl.mem_flags.WRITE_ONLY,
                                 found_limit*width*height*2)

        nfound_data = np.array([0], np.int32)
        nfound_buffer = cl.Buffer(ctx,
                                  cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR,
                                  hostbuf=nfound_data)

        # # I ended up not using this, but may be necessary if we want to trace
        # # solutions back to the positions they came from:
        # found_src = np.array([0]*found_limit, np.int32)
        # found_src_buffer = cl.Buffer(ctx, cl.mem_flags.WRITE_ONLY, found_limit*4)

        res_data = np.array([0]*wgs*cu, np.int32)
        res_buffer = cl.Buffer(ctx, cl.mem_flags.WRITE_ONLY, wgs*cu*4)

        # per-worker, per-cell placement counts (only filled in with --depth-stats)
        depth_data = np.zeros(wgs*cu*width*height if args.depth_stats else 1, np.uint64)
        depth_buffer = cl.Buffer(ctx, cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR, hostbuf=depth_data)

        best = 0
        best_data = np.array([0]*wgs*cu, np.int16)
        best_buffer = cl.Buffer(ctx, cl.mem_flags.WRITE_ONLY, wgs*cu*2)

        solcount = 0
        calls = 0
        gpu_seconds = 0.0  # kernel + result readback, as seen by the host
        solcount = 0
        solutions = []
        max_found = 0

        start_time = int(time.time())-1 # -1 to avoid div by 0 on the time check
        search_t0 = time.perf_counter()
        last_time = 0

        def status(calls, nodes, workers_left, found, remain1, remain2, mindepth, best):
            global node_limit
            global last_time 
            status = f'calls={calls}'
            status += f',nodes={nodes}'
            status += f',active={workers_left}'
            status += f',found={found}'
            status += f',remain={remain1}/{remain2}'
            this_time = int(time.time())-start_time
            status += f',rate={float(nodes)/1000000/this_time:.2f}'
            status += f',time={this_time}'
            status += f',mindepth={mindepth}'
            status += f',best={best}'
            status += f',complete={100*(1-prev_pct*(workers_left+remain2)/(remain1+remain2+workers_left)):.02f}%'
            # rate2 is number of assignments completed per second
            rate2 = (nassign_data[0]-wgs*cu)/this_time
            # status += ',rate2={0:.3f}'.format(rate2)
            # remain2 is number of days left based on remaining assignments and rate2
            remain2 = (len(pos_list)-nassign_data[0])/rate2/(60*60*24)
            # status += ',remain2={0:.2f}'.format(remain2)
            last_time = this_time
            print(status, flush=True)

        workers_left = wgs*cu

        def chunks(lst, n):
            """Yield successive n-sized chunks from lst."""
            for i in range(0, len(lst), n):
                yield lst[i:i + n]

        while True:
            # print('running kernel')
            kernel_t0 = time.perf_counter()
            kernel(queue, (cu*wgs,), (wgs,), piece_buffer, worker_buffer,
                   np.int32(len(pos_list)), nassign_buffer, found_buffer,
                   nfound_buffer, np.int32(limit), np.int32(width*height),
                   np.int32(node_limit), lm, res_buffer, best_buffer, depth_buffer)
            calls += 1
            cl._enqueue_read_buffer(queue, piece_buffer, piece_data)
            cl._enqueue_read_buffer(queue, worker_buffer, worker_pos)
            cl._enqueue_read_buffer(queue, nassign_buffer, nassign_data)
            #cl._enqueue_read_buffer(queue, found_buffer, found_data)
            cl._enqueue_read_buffer(queue, nfound_buffer, nfound_data)
            cl._enqueue_read_buffer(queue, res_buffer, res_data)
            cl._enqueue_read_buffer(queue, best_buffer, best_data).wait()
            call_seconds = time.perf_counter() - kernel_t0
            gpu_seconds += call_seconds
            # grow the per-launch node budget until a launch takes ~0.2 s
            if call_seconds < 0.2 and node_limit < 2**30:
                node_limit *= 2
                print('node_limit = %d' % node_limit)
            if nassign_data[0] > len(pos_list):
                nassign_data[0] = len(pos_list)
            # last_nodes = 0
            # for i in range(wgs*cu):
            #     last_nodes += int(res_data[i])
            last_nodes = int(res_data.sum())
            if last_nodes == 0:
                break
            nodes += last_nodes

            this_best = int(best_data.max())
            if this_best > best:
                best = this_best
            # for i in range(wgs*cu):
            #     if best_data[i] > best:
            #         best = best_data[i]

            if nfound_data[0] > 0:
                cl._enqueue_read_buffer(queue, found_buffer, found_data).wait()
                if nfound_data[0] > max_found:
                    max_found = nfound_data[0]
            for i in range(nfound_data[0]):
                offset = i*width*height
                offset2 = (i+1)*width*height
                pd2 = found_data[offset:offset2]
                #print('pd2 = {}'.format(pd2))
                solcount += 1
                solstr = ' '.join([str(p[0]+1)+'/'+str(p[1]) for p in [fit2[p2] for p2 in pd2.tolist()]])
                solutions += [solstr]
                print(f"solution {solcount}: {solstr}", flush=True)

            # DEBUG CODE FOR DUPS
            # pos_list2 = list(chunks(piece_data.tolist(), width*height))
            # untouched = pos_list2[nassign_data[0]:]
            # touched = [pos_list2[pos_num] for pos_num in worker_pos if pos_num != -1]
            # pos_list2 = touched + untouched
            # if len(pos_list2) > len(set(map(tuple, pos_list2))):
            #     print('dups in pos_list2', flush=True)
            #     pos_list2 = list(chunks(piece_data.tolist(), width*height))
            #     complete = set()
            #     for i in range(nassign_data[0]):
            #         if i not in worker_pos:
            #             complete.add(i)
            #     for i, pos in enumerate(pos_list2):
            #         if i in complete:
            #             continue
            #         for j, pos2 in enumerate(pos_list2):
            #             if j in complete:
            #                 continue
            #             if i < j and pos == pos2:
            #                 print(f'dups at {i} and {j} for {pos_to_str(pos)}', flush=True)
            #                 print(f'{i}: {src_list[i]}')
            #                 print(f'{j}: {src_list[j]}')
            #                 sys.exit(0)

            # if False and (len(pos_list)-nassign_data[0]) < wgs*cu:
            if (len(pos_list)-nassign_data[0]) < wgs*cu:
                # We're running out of positions for workers. deepen_search here.
                # Trim pos_list down to only active and unsearched positions.
                all_pos = piece_data.reshape(-1, width*height)

                remain1 = nassign_data[0]-wgs*cu
                remain2 = len(all_pos)-nassign_data[0]
                prev_pct *= (workers_left+remain2)/(remain1+remain2+workers_left)

                # keep positions still held by workers, then the unassigned ones,
                # each trimmed at its first -1
                keep = [pos_num for pos_num in worker_pos if pos_num != -1] +                     list(range(nassign_data[0], len(all_pos)))
                kept = all_pos[keep]
                empty = kept == -1
                lengths = np.where(empty.any(axis=1), empty.argmax(axis=1), width*height)
                pos_list = [row[:n].tolist() for row, n in zip(kept, lengths)]
                if do_trace:
                    untouched_src = src_list[nassign_data[0]:]
                    touched_src = [src_list[pos_num] for pos_num in worker_pos if pos_num != -1]
                    src_list = touched_src + untouched_src
                # if len(pos_list) > len(set(map(tuple, pos_list))):
                #     print('dups in pos_list')
                #     print(f'len(touched) = {len(touched)}')
                #     print(f'len(untouched) = {len(untouched)}')
                #     for i, pos in enumerate(pos_list):
                #         for j, pos2 in enumerate(pos_list):
                #             if i < j and pos == pos2:
                #                 print(f'dups at {i} and {j} for {pos_to_str(pos)}')
                #     sys.exit(0)
                while len(pos_list) < wgs*cu*2 and len(pos_list) > 0:
                    pos_list2 = []
                    src_list2 = []
                    nodes += deepen_list(pos_list, src_list, pos_list2, src_list2, limit, False)
                    pos_list = pos_list2
                    src_list = src_list2
                    limit += 1
                    print('%d positions after extending to depth %d' % (len(pos_list), limit), flush=True)
                    if len(pos_list) > 0 and limit > best:
                        best = limit;
                    if limit == width*height:
                        print('found solutions by deepening:')
                        for pos in pos_list:
                            del pos[width*height:]
                            solstr = ' '.join([str(p[0]+1)+'/'+str(p[1]) for p in [fit2[p2] for p2 in pos]])
                            solutions += [solstr]
                            solcount += 1
                            print(f'solution {solcount}: {solstr}')
                        pos_list = []
                if len(pos_list) == 0:
                    break

                piece_data = list_to_np(pos_list)
                # reassign workers
                for i in range(wgs*cu):
                    worker_pos[i] = i
                nassign_data[0] = wgs*cu
                piece_buffer = cl.Buffer(ctx,
                                         cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR,
                                         hostbuf=piece_data)
            else:
                cl._enqueue_write_buffer(queue, piece_buffer, piece_data)

            if calls % 10 == 0:
                workers_left = 0
                for i in worker_pos:
                    if i != -1:
                        workers_left += 1
                status(calls, nodes, workers_left, solcount, nassign_data[0]-wgs*cu,
                       len(pos_list)-nassign_data[0], limit, best)

            nfound_data[0] = 0
            cl._enqueue_write_buffer(queue, worker_buffer, worker_pos)
            cl._enqueue_write_buffer(queue, nassign_buffer, nassign_data)
            cl._enqueue_write_buffer(queue, nfound_buffer, nfound_data)

            if args.time_limit and time.perf_counter() - search_t0 >= args.time_limit:
                print('time limit reached; search incomplete')
                break
        if not (args.time_limit and time.perf_counter() - search_t0 >= args.time_limit):
            print('complete=100.00%', flush=True)
        print(f'search_seconds = {time.perf_counter() - search_t0:.2f}')
        print(f'gpu_seconds = {gpu_seconds:.2f}')
        print(f'kernel_calls = {calls}')
        print('nodes = {}'.format(nodes+nodes1))
        if args.depth_stats:
            cl._enqueue_read_buffer(queue, depth_buffer, depth_data).wait()
            per_depth = depth_data.reshape(-1, width*height).sum(axis=0)
            print(f'depth_stats_total = {int(per_depth.sum())} (kernel nodes; host deepen nodes not included)')
            for d, n in enumerate(per_depth):
                if n:
                    print(f'depth_nodes {d} {int(n)}')
        print('num solutions = {}'.format(solcount))
        # print('max_found = {}'.format(max_found))
        print(f'best = {best}')
        url = "https://puzzlingaddiction.com/e2db/store_result"
        payload = {
            "puzzle": args.puzzle,
            "row_num": row_num,
            "nodes": nodes,
            "best": best,
            "solutions": solcount,
            "reporter": args.reporter if args.reporter else 'anonymous',
            "hostname": (socket.gethostname() + args.hostname_suffix)[:32],
            "update_dttm": datetime.now(timezone.utc).isoformat()
        }
        print(f'payload = {payload}')
        if not args.noreport:
            auth_object = HTTPDigestAuth('reporter', get_password())
            response = requests.post(url, json=json.dumps(payload), auth=auth_object)
            print(f'response status = {response.status_code}')
            print(response.text)
            if not response.ok:
                break
        if not random_partial or args.time_limit:
            break
        if args.max_hours and time.time() - program_start >= args.max_hours*3600:
            print(f'--max-hours {args.max_hours} reached; not starting another row', flush=True)
            break
