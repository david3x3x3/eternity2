#!/usr/bin/env python
import sys
import pyopencl as cl
import numpy as np
import time
import os
import random
import argparse
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

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--clinfo", help="print OpenCL information and exit", action="store_true")
    parser.add_argument("--platform", help="OpenCL platform number", type=int, default=0)
    parser.add_argument("--device", help="OpenCL device number", type=int, default=0)
    parser.add_argument("--maxcu", help="max compute units", type=int)
    parser.add_argument("--puzzle", help="puzzle name, e.g. 10x10_1", type=str)
    parser.add_argument("--partial", help="specifying which part of a puzzle to search (e.g. 10,r) for rowsize 10, random row", type=str)

    args = parser.parse_args()
    for i in range(len(cl.get_platforms())):
        p = cl.get_platforms()[i]
        print('Plaform ' + str(i) + ': ' + p.name)
        for j in range(len(p.get_devices())):
            d = p.get_devices()[j]
            print('  Device ' + str(j) + ': ' + str(d.name) + ' (' + str(d.type) + ')')

    platform = cl.get_platforms()[args.platform]
    device = platform.get_devices()[args.device]

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
    fn = f'pieces_set_{puzzset}/pieces_{puzzname}.txt'
    fp=open(fn,'r')
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

    fp = open('eternity2_kernel.cl','r')
    prgsrc = fp.read()
    fp.close()

    # print('fit1 =', fit1)
    # print('fit2 =', fit2)
    # print('fit2c =', fit2c)
    prgsrc = prgsrc.replace('KMEMTYPE','local')
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
    #print(kernel)

    print('kernel.LOCAL_MEM_SIZE = ' + str(kernel.get_work_group_info(cl.kernel_work_group_info.LOCAL_MEM_SIZE, device)))

    # print(f'fit1 (len {len(fit1)}) = ' + str(fit1))
    # print(f'fit2 (len {len(fit2)}) = ' + str(fit2))

    maxcu = device.max_compute_units
    wgs = device.local_mem_size//(width*height*2)
    if device.type != cl.device_type.GPU:
        wgs = 1
    if device.max_work_group_size < wgs:
        wgs = device.max_work_group_size
    if wgs > 100:
        # sometimes this estimate is off, and we run out of memory
        wgs -= 1

    print('wgs = ' + str(wgs))
    cu = device.max_compute_units
    if args.maxcu:
        cu = min(cu, args.maxcu)
    print('cu = ' + str(cu))
    lm = cl.LocalMemory(wgs*(width*height*2))
    print('total workers = %d' % (wgs*cu))

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
    while True:
        if depth == 0:
            fn = f'{puzzname}-{limit}-cached.txt'
            if os.path.exists(fn):
                depth = limit
                with open(fn, 'r') as fp:
                    pos_list = []
                    print(f'reading stored row data')
                    print(f'search_args = {search_args}, i = {i}')
                    if i+1 == len(search_args):
                        # just pick one row
                        if search_args[i] == 'r':
                            #this probably defeats my goals of not reading lots of stuff into memory
                            lines = fp.readlines()
                            j = random.randrange(len(lines)) 
                            search_args[i] = '%d*' % j
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
                j = random.randrange(len(pos_list))
                search_args[i] = '%d*' % j
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
        piece_data = np.array([-1]*width*height*len(pl), np.int16)
        for i, pos in enumerate(pl):
            # print(f'encoding pos {i}: {pos_to_str(pos)} ({pos})')
            for j, val in enumerate(pos):
                if j < width*height:
                    piece_data[width*height*i+j] = val
        return piece_data

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

    best = 0
    best_data = np.array([0]*wgs*cu, np.int16)
    best_buffer = cl.Buffer(ctx, cl.mem_flags.WRITE_ONLY, wgs*cu*2)

    solcount = 0
    calls = 0
    solcount = 0
    solutions = []
    max_found = 0

    start_time = int(time.time())-1 # -1 to avoid div by 0 on the time check
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
        # rate2 is number of assignments completed per second
        rate2 = (nassign_data[0]-wgs*cu)/this_time
        # status += ',rate2={0:.3f}'.format(rate2)
        # remain2 is number of days left based on remaining assignments and rate2
        remain2 = (len(pos_list)-nassign_data[0])/rate2/(60*60*24)
        # status += ',remain2={0:.2f}'.format(remain2)
        if last_time != 0 and this_time - last_time < 2:
            node_limit *= 2
            print('node_limit = %d' % node_limit)
        last_time = this_time
        print(status, flush=True)

    workers_left = wgs*cu

    def chunks(lst, n):
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    while True:
        # print('running kernel')
        kernel(queue, (cu*wgs,), (wgs,), piece_buffer, worker_buffer,
               np.int32(len(pos_list)), nassign_buffer, found_buffer,
               nfound_buffer, np.int32(limit), np.int32(width*height),
               np.int32(node_limit), lm, res_buffer, best_buffer)
        calls += 1
        cl._enqueue_read_buffer(queue, piece_buffer, piece_data)
        cl._enqueue_read_buffer(queue, worker_buffer, worker_pos)
        cl._enqueue_read_buffer(queue, nassign_buffer, nassign_data)
        #cl._enqueue_read_buffer(queue, found_buffer, found_data)
        cl._enqueue_read_buffer(queue, nfound_buffer, nfound_data)
        cl._enqueue_read_buffer(queue, res_buffer, res_data)
        cl._enqueue_read_buffer(queue, best_buffer, best_data).wait()
        if nassign_data[0] > len(pos_list):
            nassign_data[0] = len(pos_list)
        # last_nodes = 0
        # for i in range(wgs*cu):
        #     last_nodes += int(res_data[i])
        last_nodes = int(res_data.sum())
        if last_nodes == 0:
            break
        nodes += last_nodes

        this_best = best_data.max()
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
            pos_list = list(chunks(piece_data.tolist(), width*height))
            untouched = pos_list[nassign_data[0]:]
            touched = [pos_list[pos_num] for pos_num in worker_pos if pos_num != -1]
            pos_list = touched + untouched
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
            for posnum, pos in enumerate(pos_list):
                if -1 in pos:
                    del pos[pos.index(-1):]
                # print(f'posnum={posnum},limit={limit}, len={len(pos)}, pos=', end='')
                # print_pos(pos)
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

    print('nodes = {}'.format(nodes+nodes1))
    print('num solutions = {}'.format(solcount))
    # print('max_found = {}'.format(max_found))
    print(f'best = {best}')
