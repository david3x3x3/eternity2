#!/usr/bin/env python
import sys
import pyopencl as cl
import numpy as np
import time

for i in range(len(cl.get_platforms())):
    p = cl.get_platforms()[i]
    print('Plaform ' + str(i) + ': ' + p.name)
    for j in range(len(p.get_devices())):
        d = p.get_devices()[j]
        print('  Device ' + str(j) + ': ' + str(d.name) + ' (' + str(d.type) + ')')

platform = cl.get_platforms()[1]
device = platform.get_devices()[0]

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
sys.stdout.flush()

ctx = cl.Context([device])
queue = cl.CommandQueue(ctx)

edgecount = 0

fp=open(sys.argv[1],'r')
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
print(pypieces)
print('edgecount = ' + str(edgecount))
fp.close()
fit = dict()
for key1, val in pieces.items():
    if val[0] == 0 and val[3] == 0 and key1[0] != 0:
        # only try one corner in top left
        continue
    key2 = (val[0], val[3], val[1] == 0, val[2] == 0)
    if not fit.get(key2):
        fit[key2] = []
    fit[key2] += [key1]

fit1 = [1]*edgecount*edgecount*4
fit2 = [None]*3
fit2c = ["{-1,0}"]*3
dummypos = -10
for f in sorted(fit):
    # print('f = ' + str(f))
    # print('  ' + str(fit[f]))
    f3 = ['{'+str(f2[0])+','+str(f2[1])+'}' for f2 in fit[f]]
    # left, up, down, right
    pos = ((f[1]*edgecount+f[0])*2+f[3])*2+f[2]
    if f[2] and f[3]:
        dummypos = len(fit2)
        # print('dummypos = ' + str(dummypos))
        # print(pieces[fit[f][0]])
    if len(f3) > 0:
        fit1[pos] = len(fit2)
        fit2 = fit2 + fit[f] + [None]
        fit2c = fit2c + f3 + ['{-1,0}']
    else:
        fit1[pos] = 2

fp = open('eternity2_kernel.cl','r')
prgsrc = fp.read()
fp.close()

#print('fit2c =', fit2c)
prgsrc = prgsrc.replace('KMEMTYPE','local')
prgsrc = prgsrc.replace('KGLOBMEM','0')
prgsrc = prgsrc.replace('PYPIECES',pypieces)
prgsrc = prgsrc.replace('PYFITTABLE1',','.join(map(str,fit1)))
prgsrc = prgsrc.replace('PYFITTABLE2',','.join(map(str,fit2c)))
prgsrc = prgsrc.replace('PYEDGECOUNT',str(edgecount))
prgsrc = prgsrc.replace('KWIDTH',str(width))
prgsrc = prgsrc.replace('KHEIGHT',str(height))

#print('src = ' + prgsrc)
prog = cl.Program(ctx, prgsrc).build()
kernel = prog.mykernel
print(kernel)

print('kernel.LOCAL_MEM_SIZE = ' + str(kernel.get_work_group_info(cl.kernel_work_group_info.LOCAL_MEM_SIZE, device)))
      
print('fit1 = ' + str(fit1))
print('fit2 = ' + str(fit2))

def mysearch(placed, mindepth, maxdepth):
    count=0
    nodes = 0
    #print(placed)
    #print([fit2[p] for p in placed[width:]])
    # which pieces are placed (not positions)
    placed2 = [0]*width*height
    for p2 in [fit2[p] for p in placed[width:]]:
        if p2:
            placed2[p2[0]] = 1

    while len(placed)-width > mindepth:
        i = placed[-1]
        if fit2[i]:
            # decrement the count of the piece we previously tried
            placed2[fit2[i][0]] -= 1
        # try the next piece
        placed[-1] += 1
        i = placed[-1]
        if not fit2[i]:
            # no more pieces to try here
            del placed[-1:]
            continue

        ii = fit2[i][0]

        # count how many times we have placed this piece
        placed2[ii] += 1
        if placed2[ii] > 1:
            # skip if we've already placed it somewhere else
            continue

        nodes += 1
        
        if len(placed) == (width+1)*height:
            return nodes
            # for p in [fit2[p2] for p2 in placed[width:]]:
            #     print('/'.join(map(str,p)), end=' ')
            # print('')
            print(str(count) + ': ', end = '')
            print(' '.join([str(p[0]+1)+'/'+str(p[1]) for p in [fit2[p2] for p2 in placed[width:]]]))
            sys.stdout.flush()
            count += 1
            continue

        up=pieces[fit2[placed[-width]]][2]
        left=pieces[fit2[placed[-1]]][1]
        right = int(len(placed) % width == width - 1)
        down = int(len(placed) // width == height)
        placed += [fit1[((left*edgecount+up)*2+down)*2+right]-1]
        if len(placed) > width+maxdepth:
            return nodes
        
    print('count = ' + str(count))
    return nodes

maxcu = device.max_compute_units
wgs = device.local_mem_size//(width*height*2)
if device.max_work_group_size < wgs:
    wgs = device.max_work_group_size
print('wgs = ' + str(wgs))
cu = device.max_compute_units
print('cu = ' + str(cu))
lm = cl.LocalMemory(wgs*(width*height*2))

# which pieces are in each location. we put a row of blank pieces at
# the top so that we can always match the piece above the current one,
# even in the top row.
placed = [dummypos]*width+[2]
nodes = 0

print(len(sys.argv))
if len(sys.argv) > 2:
    limit=int(sys.argv[2])
else:
    limit = width*height
print('depth limit = ' + str(limit))

if len(sys.argv) > 3:
    node_limit=int(sys.argv[3])
else:
    node_limit = 10000
print('node limit = ' + str(node_limit))

start_time = time.time()

work_counter=0
def next_work_item(pdarray, offset):
    global nodes, placed, more_work, limit, width, work_counter

    nodes += mysearch(placed, 0, limit)
    pos_copy = placed[width:]
    if len(pos_copy) <= width:
        pdarray[offset] = 0
        more_work = False
        return False
    del placed[-1:]
    for i in range(len(pos_copy)):
        pdarray[offset+i] = pos_copy[i]
    pdarray[len(pos_copy)] = 0
    work_counter += 1
    return True

piece_data = np.array([0]*width*height*wgs*cu, np.int16)

more_work = True
work_item = 0
while work_item < wgs*cu:
    #print('search #' + str(work_item))
    if not next_work_item(piece_data, work_item*width*height):
        break
    work_item += 1

res_data = np.array([0]*wgs*cu, np.int32)
res_buffer = cl.Buffer(ctx, cl.mem_flags.WRITE_ONLY, wgs*cu*4)
#                       hostbuf=res_data)

piece_buffer = cl.Buffer(ctx,
                         cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR,
                         hostbuf=piece_data)

solcount = 0
calls = 0
while True:
    prog.mykernel(queue, (cu*wgs,), (wgs,), piece_buffer, np.int32(limit),
                  np.int32(width*height), np.int32(node_limit), lm, res_buffer)
    calls += 1

    cl.enqueue_read_buffer(queue, piece_buffer, piece_data).wait()
    cl.enqueue_read_buffer(queue, res_buffer, res_data).wait()

    done = True
    last_nodes = 0
    for i in range(wgs*cu):
        last_nodes += int(res_data[i])
        offset = i*width*height
        offset2 = (i+1)*width*height
        pd2 = piece_data[offset:offset2]
        #print('pd2', pd2)

        zeros = np.where(pd2 == 0)[0]
        if len(zeros) == 0:
            #print('solution', ' '.join([str(p[0]+1)+'/'+str(p[1]) for p in [fit2[p2] for p2 in pd2]]))
            #sys.stdout.flush()
            solcount += 1
            done = False
        elif zeros[0] <= limit:
            piece_data[offset] = 0
            if more_work:
                if next_work_item(piece_data, offset):
                    done = False
        else:
            done = False
    nodes += last_nodes
    if calls % 10 == 0:
        print('nodes = ' + str(nodes) + ', solcount = ' + str(solcount) + ', rate = ' + str((nodes/(time.time()-start_time))/1000000))
        print('efficiency = ' + str(((last_nodes/(wgs*cu))/node_limit)*100))
        sys.stdout.flush()
    if done:
        break
    cl.enqueue_write_buffer(queue, piece_buffer, piece_data).wait()
print('done nodes = ' + str(nodes) + ', solcount = ' + str(solcount) + ', rate = ' + str((nodes/(time.time()-start_time))/1000000))
