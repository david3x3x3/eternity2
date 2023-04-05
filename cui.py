# based on https://stackoverflow.com/questions/375427/a-non-blocking-read-on-a-subprocess-pipe-in-python/4896288

import sys, random, re, msvcrt, webbrowser
from subprocess import PIPE, Popen
from threading  import Thread
from queue import Queue, Empty
from time import sleep

procs = 10

ON_POSIX = 'posix' in sys.builtin_module_names

def enqueue_output(out, queue, num):
    for line in iter(out.readline, b''):
        queue.put((num, line.decode('utf-8').strip()))
    out.close()

def print_best():
    global log
    board = bests[curs].split(':')
    if len(board) > 1:
        board = board[1].strip().split(' ')
    else:
        board = []
    log = list(board)
    rs = procs+2
    for r in range(16):
        goto_rc(rs, 1, False)
        rs += 1
        for c in range(16):
            i = r*16+c
            if i < len(board):
                p, rot = map(int,board[i].split('/'))
                #print('%02x ' % (p-1), end='')
                print('%3d/%d ' % (p, rot), end='')
            else:
                print('..... ', end='')
    print('', end='', flush=True)
    print_url()

def line_to_url(line):
    board = line.split(':')
    if len(board) > 1:
        board = board[1].strip().split(' ')
    else:
        board = []
    myurl = 'https://e2.bucas.name/#puzzle=EternityII&board_w=16&board_h=16&board_edges='
    for i in range(256):
        if i < len(board):
            p, rot = map(int,board[i].split('/'))
            for rot2 in range(4):
                myurl += 'animovhuqprslwtjgkbdecf'[pypieces[p-1][(6-rot+rot2)%4]]
        else:
            myurl += '0000'
    return myurl
    
def print_url():
    global url, urlf
    
    mystr = bests[curs]
    url = line_to_url(mystr)
    pieces = list(map(int,[s.split('/')[0] for s in mystr.split(':')[1].strip().split(' ')]))
    corners = set(list(range(1,5)))
    edges = set(list(range(5,61)))
    middle = set(list(range(61,257)))
    for n in pieces:
        corners.discard(n)
        edges.discard(n)
        middle.discard(n)
    total = len(pieces)
    while total < 256:
        row = (total)//16
        col = (total)%16
        if col == 0:
            if row == 0:
                mystr += f' {corners.pop()}/1'
            elif row == 15:
                mystr += f' {corners.pop()}/0'
            else:
                mystr += f' {edges.pop()}/1'
        elif col == 15:
            if row == 0:
                mystr += f' {corners.pop()}/2'
            elif row == 15:
                mystr += f' {corners.pop()}/3'
            else:
                mystr += f' {edges.pop()}/3'
        else:
            if row == 0:
                mystr += f' {edges.pop()}/2'
            elif row == 15:
                mystr += f' {edges.pop()}/0'
            else:
                mystr += f' {middle.pop()}/0'
        total += 1
    urlf = line_to_url(mystr)

q = Queue()

all_processes = [None]*procs

def start_proc(n):
    global all_processes
    cmd = f'./eternity2-gen.exe {n} 0 1'
    p = Popen(cmd, stdout=PIPE, bufsize=1, close_fds=ON_POSIX)
    all_processes[n] = p
    t = Thread(target=enqueue_output, args=(p.stdout, q, n))
    t.daemon = True # thread dies with the program
    t.start()

for n in range(procs):
    start_proc(n)

fp=open('eternity2.txt','r')
width, height = list(map(int,fp.readline().strip('\n').split(' ')))
pieces = dict()
piecenum=0
pypieces = []
edgecount=0
for line in fp.read().splitlines():
    t1 = tuple(map(int,line.split(' ')))
    pypieces += [t1]
    if max(t1) >= edgecount:
        edgecount = max(t1) + 1
    for rot in range(4):
        pieces[(piecenum,rot)] = t1[-rot:] + t1[:-rot]
    piecenum += 1
#print('pypieces = ' + str(pypieces))
#print('edgecount = ' + str(edgecount))
fp.close()
#exit(0)

curs=0

def goto_rc(r, c, doflush):
    print('%c[%d;%dH' % (27, r, c), flush=doflush, end='')
    
bests = []
for i in range(procs):
    bests += ['']
statuses = []
for i in range(procs):
    statuses += ['']

def print_status(num, hilight):
    goto_rc(num+1, 1, True)
    if num == curs and hilight:
        print('%c[7m' % 27, end='')
    print('%X %s%c[m ' % (num, statuses[num], 27), flush=hilight, end='')

print(f'{27:c}[2J',end='')
while True:
    # read line without blocking
    try:  num, line = q.get_nowait() # or q.get(timeout=.1)
    except Empty:
        if msvcrt.kbhit():
            while msvcrt.kbhit():
                c = msvcrt.getch().decode('ascii')
                if c == 'q': # quit
                    for p in all_processes:
                        if p:
                            p.kill()
                    goto_rc(16+procs+2,1, False)
                    exit(0)
                elif c == 'j': # next row
                    if curs + 1 >= procs:
                        continue
                    print_status(curs, False)
                    curs += 1
                    print_status(curs, True)
                    print_best()
                    goto_rc(curs+1, 1, False)
                elif c == 'k': # previous row
                    if curs < 1:
                        continue
                    print_status(curs, False)
                    curs -= 1
                    print_status(curs, True)
                    print_best()
                    goto_rc(curs+1, 1, False)
                elif c == 'v': # view on bucas.name
                    webbrowser.open(url)
                elif c == 'f': # fill remainder with random valid pieces and view
                    webbrowser.open(urlf)
                elif c == 'r': # restart
                    all_processes[curs].kill()
                    start_proc(curs)
                elif c == f'{12:c}': # refresh (^L)
                    print(f'{27:c}[2J',end='')
                    for n in range(procs):
                        if n != curs:
                            print_status(n, False)
                    print_status(curs, True)
                    print_best()
                    goto_rc(curs+1, 1, False)
                elif c == 'o': # launch script to process current output
                    pargs = ['C:/Users/David/Downloads/pypy3.8-v7.3.7-win64/pypy3.exe','finish.py'] + log
                    proc = Popen(pargs,stdout=PIPE)
                    for line in proc.stdout:
                        webbrowser.open(line_to_url(line.decode('utf-8').rstrip()))
        else:
            sleep(0.2)
        #print('no output yet')
    else: # got line
        if re.match('^status', line):
            statuses[num] = line
            print_status(num, True)
            goto_rc(curs+1, 1, False)
        if re.match('^best', line):
            bests[num] = line
            if curs == num:
                print_best()
