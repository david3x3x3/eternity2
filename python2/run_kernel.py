import sys
import pyopencl as cl
import numpy

edgecount = 0

#print('reading piece data')
# read the piece definition file
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
#print('pypieces = ' + str(pypieces))
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

print('fit1 =', fit1)
print('fit2 =', fit2)

# Create context and command queue
platform = cl.get_platforms()[0]
devices = platform.get_devices()
ctx = cl.Context(devices)
queue = cl.CommandQueue(ctx)

cu = devices[0].max_compute_units
print('cu = %d' % cu)
#wgs = devices[0].local_mem_size // (2*(width*height+1))
wgs = devices[0].local_mem_size // (3*(width*height)+4)
print('target wgs = %d' % wgs)
maxwgs = devices[0].max_work_group_size
print('max wgs = %d' % maxwgs)
if wgs > maxwgs:
   wgs = maxwgs
print('wgs = %d' % wgs)
print('wgs*cu = %d' % (wgs*cu))

# Open program file and build
program_file = open('solve.cl', 'r')
program_text = program_file.read()
program_text = program_text.replace('PYPIECES',pypieces)
program_text = program_text.replace('PYFITTABLE1',','.join(map(str,fit1)))
program_text = program_text.replace('PYFITTABLE2',','.join(map(str,fit2c)))
program_text = program_text.replace('PYEDGECOUNT',str(edgecount))
program_text = program_text.replace('KWIDTH',str(width))
program_text = program_text.replace('KHEIGHT',str(height))
print('program_text =', program_text)
program = cl.Program(ctx, program_text)
try:
   program.build()
except:
   print("Build log:")
   print(program.get_build_info(devices[0], cl.program_build_info.LOG))
   raise

limit = numpy.int32(1)
# lm_placed is the current search state with piece and orientation in each position
lm_placed = cl.LocalMemory(wgs*(width*height) * 2)
# lm_used is to keep track of which pieces are used
lm_used = cl.LocalMemory(wgs*width*height)

lm_mindepth = cl.LocalMemory(wgs*2)
lm_depth = cl.LocalMemory(wgs*2)

search_data = numpy.array([-1]*(wgs*cu*(width*height+1)), numpy.int16)
search_data[0] = 0
search_buffer = cl.Buffer(ctx, 
                          cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR, 
                          hostbuf=search_data)
nfound_data = numpy.array([0], numpy.int32)
nfound_buffer = cl.Buffer(ctx,
                          cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR,
                          hostbuf=nfound_data)

res_data = numpy.array([0]*wgs*cu, numpy.int32)
res_buffer = cl.Buffer(ctx, cl.mem_flags.WRITE_ONLY, wgs*cu*4)

nodes = 0
calls = 0
active=1
while active > 0:
   # Create, configure, and execute kernel
   program.solve(queue, (wgs*cu,), (wgs,), limit, search_buffer, nfound_buffer, lm_placed, lm_used, lm_mindepth, lm_depth, res_buffer)
   calls += 1
   #if calls % 10 == 0:
   #print('reading results')
   cl._enqueue_read_buffer(queue, search_buffer, search_data)
   cl._enqueue_read_buffer(queue, res_buffer, res_data)
   cl._enqueue_read_buffer(queue, nfound_buffer, nfound_data).wait()

   nodes2 = sum(res_data)
   nodes += nodes2
   
   if calls % 1 == 0:
      active = 0
      for i in range(wgs*cu):
         if search_data[i] >= 0:
            active += 1
            x = [(fit2[x][0]+1,fit2[x][1]) for x in list(search_data[wgs*cu+width*height*i:wgs*cu+width*height*(i+1)]) if x != -1]
            #if len(x) == width*height:
            print('%d (%d): %s' % (i, search_data[i], ' '.join(['/'.join(map(str,y)) for y in x])), flush=True)
      status = 'calls = %d' % calls
      status += ', active = %d' % active
      status += ', nodes = %d' % nodes
      status += ', nfound = %d' % nfound_data[0]
      print(status, flush=True)

   #print('writing search_data')
   cl._enqueue_write_buffer(queue, search_buffer, search_data)
   cl._enqueue_write_buffer(queue, nfound_buffer, nfound_data)
