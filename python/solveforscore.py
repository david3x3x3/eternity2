#!/usr/bin/env python3
import random, time

piece_data = """
bdaa/beaa/cdaa/dcaa/gbab/hcab/jbab/jfab/mdab/oeab/pcab/teab/tfab/veab/hbac/idac/
kfac/nfac/ocac/pcac/qeac/rbac/rfac/sbac/vbac/gcad/gdad/hdad/idad/ofad/pcad/sdad/
tcad/tead/ufad/wead/ibae/lfae/mfae/ncae/ndae/pbae/pcae/pdae/qbae/seae/teae/ueae/
gfaf/hbaf/hcaf/jbaf/oeaf/qeaf/qfaf/tdaf/ubaf/ufaf/vcaf/wdaf/jigg/kogg/hlgh/gtgi/
iwgi/kkgi/mhgi/sjgi/wtgi/logl/orgl/kigm/pqgm/spgm/tlgm/kpgn/npgn/lugo/slgo/uvgo/
nigp/iigq/mqgq/ingr/jkgr/trgr/usgr/gvgs/jwgs/qugs/mrgt/npgt/nqgt/qvgt/rkgt/vlgv/
qngw/stgw/vjgw/wvgw/rphh/ruhh/unhh/wjhh/qphi/lthj/nthj/qphj/umhj/prhk/rphk/snhl/
suhl/kqhm/orhm/rmhm/wuhm/lvhn/urho/twhp/kwhq/juhs/knhs/sphs/rwht/vpht/kjhu/nvhu/
qlhu/sthu/jshv/rkhv/kuhw/mqhw/qlhw/ushw/soii/jlij/jmij/jrij/nvij/pjij/urij/vvij/
lqik/iril/iwil/lkil/pril/jmin/qwin/mmio/mnio/wuio/ooiq/oriq/woiq/ouis/tjis/vvit/
jsiu/ksiu/pmiw/quiw/lqjk/qtjk/lljm/mpjn/nvjn/qtjo/sujo/vmjo/ppjp/rsjp/ovjq/onjr/
kqjs/rujt/tpjt/ouju/mujv/omjv/ntkk/wokl/nrkm/ttkm/vokn/kvko/lnko/unko/llkp/pskp/
mokq/vmkr/vwkr/wpkr/mwks/ntks/ssks/nlkt/vtku/woku/rnkv/rtkv/ulkv/wvkv/woll/nwlm/
tplm/mnlo/uplo/lulp/ttlq/lslr/qwlr/wvlr/npls/qrlu/mqlv/mulw/vvlw/vwlw/rwmm/somm/
upmm/npmo/rrmo/ntmq/owms/utms/rsmt/rvmt/nsnn/uqno/oqnq/osnq/rpnq/qunr/pwns/vpns/
ovnt/qvnt/prop/stop/wsoq/uwov/vwpp/rqpq/qvpr/uvps/wtqq/trqr/usrt/vusu/uwsw/vwtw
"""

width, height = (16,16)
pieces = dict()
piecenum=1
for s in ''.join(piece_data.split('\n')).split('/'):
    t1 = tuple((ord(c)-ord('a') for c in s))
    for rot in range(4):
        pieces[(piecenum,rot)] = t1[-rot:] + t1[:-rot]
    piecenum += 1
fit = dict()
for key1, val in pieces.items():
    key2 = (val[0], val[3], val[1] == 0, val[2] == 0)
    if not fit.get(key2):
        fit[key2] = [key1]
    else:
        fit[key2].insert(0,key1)
hints = { 135: (139,2), 34: (208,3), 45: (255,3), 210: (181, 3), 221: (249, 0) }
#hints = { 135: (139,2) }
#hints = {}
hintp = [hints[x][0] for x in hints]

scoretarget = 0
#scoretarget = 256458

def init():
    global solcount, nodes, highscore, highdisp, start_time, scoretarget, pieceorder
    start_time = int(time.time()-1)
    solcount = 0
    nodes = 0
    highscore = scoretarget
    highdisp = 0
    for k in fit:
        random.shuffle(fit[k])
    pieceorder = list(pieces.keys())
    random.shuffle(pieceorder)

# zig zag last 3 rotated
if True:
    order = []
    for col in range(13):
        for row in range(16):
            order += [row*width+col]
    for row in range(16):
        for col in range(13, 16):
            order += [row*width+col]

minpos = 256
maxpos = 0
stuck = True
first208=0

def nodefmt(x):
    mag = 0
    if x < 1000:
        return str(x)
    while x >= 1000:
        mag += 1
        x /= 1000
    return f'{x:.2f}{" kmgtpezyb"[mag]}'

def search2(start_layout, goal_pos, skip_allow2, orig_skips, orig_score):
    global nodes, highscore, minpos, maxpos, stuck, highdisp, first208

    remain = set(range(1,width*height+1)) - set([p[0] for p in start_layout if p])
    Q = [(list(start_layout), remain, 0, orig_score)]
    while Q:
        solution, remain, skips, score = Q.pop()
        nodes += 1

        if nodes > 500000 and stuck:
            print('restarting')
            return []

        if nodes % 200000 == 0:
            t = int(time.time())-start_time
            print(f'nodes = {nodefmt(nodes)}, range = {minpos}-{maxpos}, rate = {nodefmt(nodes//t)}     ', end='\r')
            minpos = 256
            maxpos = 0
        count = score // 1000

        if count >= 160:
            stuck = False
        
        if count == 208 and first208 == 0:
            first208 = nodes

        if score > highdisp:
            highdisp = score
            if score > highscore:
                highscore = score
            disp = list(solution)
            print(f'\n{count}:')
            for i, x in enumerate(disp):
                if i > 0 and i%width == 0:
                    print('')
                if x:
                    print(f'{x[0]:3d}/{x[1]%4}', end = ' ')
                else:
                    print('  ?  ', end = ' ')
            print('')
            print(f'nodes = {nodefmt(nodes)}, score = {score}, first208 = {nodefmt(first208)}, skips = {"+".join(map(str,glob_skiplist+[skips]))}={skips+orig_skips}', flush=True)

        if count >= goal_pos:
            yield [list(solution), skips+orig_skips, score]
            continue
        pos = order[count]
        newscore = 2
        if pos < width:
            up = 0
            newscore -= 1
        else:
            up = pieces[solution[pos-width]][2]
        if pos % width == 0:
            left = 0
            newscore -= 1
        else:
            left = pieces[solution[pos-1]][1]
        matches_l = fit.get((up, left, pos % width == width - 1, pos // width == height-1),[])
        if skips < skip_allow2:
            pool = pieceorder
        else:
            pool = matches_l
        for p in pool:
            (piecenum, rot) = p
            if piecenum not in remain:
                continue
            if pos not in hints and piecenum in hintp:
                continue
            if pos in hints and hints[pos] != p:
                continue
            if pos + 16 in hints and pieces[p][2] != pieces[hints[pos+16]][0]:
                continue
            if pos + 1 in hints and pieces[p][1] != pieces[hints[pos+1]][3]:
                continue
            newskips = 0
            if skips < skip_allow2:
                pc = pieces[p]
                if pc[0] != up:
                    newskips += 1
                if pc[3] != left:
                    newskips += 1
                if newskips+skips > skip_allow2:
                    continue
                if ((pos % width == 0) != (pc[3] == 0) or
                    (pos // width == 0) != (pc[0] == 0) or
                    (pos % width == width-1) != (pc[1] == 0) or
                    (pos // width == height-1) != (pc[2] == 0)):
                    continue
            solution2 = list(solution)
            solution2[pos] = p

            if count < minpos:
                minpos = count
            if count > maxpos:
                maxpos = count
            Q += [(solution2, remain - set([piecenum]), skips + newskips,
                   score + 1000 + newscore - newskips)]

glob_skiplist = []

def search1(start, skiplist):
    global glob_skiplist

    glob_skiplist = skiplist
    target = sum((192,16,15,12, 9, 6, 6)[:len(skiplist)+1])
    limit =      (  0, 3,30,24,18,12,12)[len(skiplist)]
    #limit =      (  0, 3,30, 5, 4, 4, 4)[len(skiplist)]
    for skip in range(limit+1):
        if 256000 + 480 - skip - start[1] <= highscore:
            # this many skips will never lead to a highscore
            return
        for res in search2(start[0], target, skip, start[1], start[2]):
            if target >= 256 or res[1]-start[1] < skip:
                # either we're done or we found a result with fewer skips than we asked for
                # in which case we already searched that result in a previous iteration
                continue
            search1(res, skiplist+[skip])

while True:
    # loop because lack of early progress could cause us to abort
    init()
    search1(([None]*height*width, 0, 0), [])
