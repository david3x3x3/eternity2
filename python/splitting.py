"""Work splitting for solve.py: positions with per-position base depths.

A position is a row of width*height fit2 indices: cells 0..top-1 hold the
placed pieces, cell `top` holds the current candidate (either one already
searched or the "one before the first candidate" index), and the rest are -1.
Its base b <= top: the kernel searches the position until it backtracks above
cell b. The remaining work of a position is the untried siblings after
row[k] at every level k from b to top.

Splitting a position at its base level b moves the siblings after row[b] into
new positions (one per sibling, each placed and with base b+1) and raises the
position's own base to b+1, or drops it when top == b. Each new placement is
counted as a node, which the kernel would otherwise have counted, so node
counts stay exact.

All of this is vectorized with numpy over many positions at once.
"""
import numpy as np


class Splitter:
    def __init__(self, fit1, fit2, pieces, width, height, edgecount):
        self.W, self.H, self.n = width, height, width*height
        self.edgecount = edgecount
        nf = len(fit2)
        # index nf is a sentinel for -1 entries (no piece, colors 0)
        self.piece = np.full(nf + 1, -1, np.int32)
        self.right = np.zeros(nf + 1, np.int32)
        self.bottom = np.zeros(nf + 1, np.int32)
        for i, e in enumerate(fit2):
            if e is not None:
                self.piece[i] = e[0]
                self.right[i] = pieces[e][1]
                self.bottom[i] = pieces[e][2]
        self.pre = np.array(fit1, np.int32) - 1      # key -> "one before the first candidate"
        runs, run = [], 0
        for e in fit2:
            run = run + 1 if e is not None else 0
            runs.append(run)
        self.max_list = max(runs)
        cells = np.arange(self.n)
        self.flags = ((cells // width == height - 1) * 2 + (cells % width == width - 1)).astype(np.int32)
        if max(e[0] for e in fit2 if e is not None) >= 128:
            raise ValueError('splitter supports at most 128 pieces')

    def tops(self, rows):
        """Index of the last non-negative cell of each row."""
        filled = rows >= 0
        return self.n - 1 - np.argmax(filled[:, ::-1], axis=1)

    def _used(self, rows, upto):
        """128-bit masks (lo, hi) of the pieces in cells 0..upto-1 of each row."""
        lo = np.zeros(len(rows), np.uint64)
        hi = np.zeros(len(rows), np.uint64)
        nf = len(self.piece) - 1
        for c in range(int(upto.max()) if len(rows) else 0):
            p = self.piece[np.where(rows[:, c] >= 0, rows[:, c], nf)]
            sel = (c < upto) & (p >= 0)
            plo = sel & (p < 64)
            phi = sel & (p >= 64)
            lo[plo] |= np.left_shift(np.uint64(1), p[plo].astype(np.uint64))
            hi[phi] |= np.left_shift(np.uint64(1), (p[phi] - 64).astype(np.uint64))
        return lo, hi

    def split(self, rows, bases):
        """Split every given position at its base level.

        Returns (children, child_bases, keep, new_bases, nodes, best, solutions):
        children are the new positions (base b+1); keep marks the parents that
        still have work (top > b); new_bases are the parents' bases (b+1);
        nodes is the number of placements made; best the deepest cell count
        reached by them (0 if none); solutions the completed boards.
        """
        rows = np.asarray(rows, np.int16)
        bases = np.asarray(bases, np.int32)
        k = len(rows)
        ar = np.arange(k)
        tops = self.tops(rows)
        cur = rows[ar, bases].astype(np.int32)
        lo, hi = self._used(rows, bases)
        # siblings after the current candidate: cur+1, cur+2, ... up to the list end
        js = np.arange(1, self.max_list + 1)
        idx = cur[:, None] + js[None, :]
        idx = np.minimum(idx, len(self.piece) - 1)
        p = self.piece[idx]
        alive = np.cumprod(p >= 0, axis=1).astype(bool)
        pu = np.where(p >= 0, p, 0).astype(np.uint64)
        is_lo = p < 64
        bit = np.where(is_lo, np.left_shift(np.uint64(1), np.where(is_lo, pu, 0)),
                       np.left_shift(np.uint64(1), np.where(is_lo, 0, pu - 64)))
        used = np.where(is_lo, (lo[:, None] & bit) != 0, (hi[:, None] & bit) != 0)
        valid = alive & ~used
        pi, pj = np.nonzero(valid)
        nodes = len(pi)
        child_idx = idx[pi, pj]
        cb = bases[pi]                               # cell the child is placed in
        n = cb + 1                                   # next cell
        best = int(n.max()) if nodes else 0
        children = rows[pi].copy()
        cols = np.arange(self.n)[None, :]
        children[cols > cb[:, None]] = -1
        children[np.arange(nodes), cb] = child_idx
        # completed boards
        done = n >= self.n
        solutions = children[done]
        go = ~done
        children, n, child_idx = children[go], n[go], child_idx[go]
        # "one before the first candidate" of the next cell
        m = len(children)
        up = np.where(n >= self.W, self.bottom[np.where(n >= self.W,
                                                        children[np.arange(m), np.maximum(n - self.W, 0)], 0)], 0)
        left = self.right[child_idx]
        key = ((left*self.edgecount + up)*2 + (self.flags[np.minimum(n, self.n - 1)] >> 1))*2 + \
            (self.flags[np.minimum(n, self.n - 1)] & 1)
        pre = self.pre[key]
        # drop children whose next cell has no candidates (the kernel would do no work)
        has = self.piece[np.minimum(pre + 1, len(self.piece) - 1)] >= 0
        children, n, pre = children[has], n[has], pre[has]
        children[np.arange(len(children)), n] = pre
        keep = tops > bases
        return children, n.astype(np.int32), keep, bases + 1, nodes, best, solutions


    def split_until(self, rows, bases, target):
        """Split positions, shallowest base first, until there are at least
        `target` positions or none are left. Only as many positions as needed
        are split; the batch size comes from the growth seen so far.

        Returns (rows, bases, nodes, best, solutions).
        """
        rows = np.asarray(rows, np.int16)
        bases = np.asarray(bases, np.int32)
        nodes = best = 0
        sols = []
        growth = 2.0                                 # net new positions per split, estimated
        while 0 < len(rows) < target:
            shallow = np.nonzero(bases == bases.min())[0]
            take = shallow[:max(1, int((target - len(rows)) / growth) + 1)]
            ch, cb, keep, nb, n, b, s = self.split(rows[take], bases[take])
            nodes += n
            best = max(best, b)
            if len(s):
                sols.extend(s)
            growth = max(0.25, (len(ch) - int((~keep).sum())) / len(take))
            rest = np.ones(len(rows), bool)
            rest[take] = False
            rows = np.concatenate([rows[rest], rows[take][keep], ch])
            bases = np.concatenate([bases[rest], nb[keep], cb])
        return rows, bases, nodes, best, sols


def reference_search(rows, bases, splitter):
    """Kernel-semantics DFS over positions in pure Python, for testing.

    Returns (nodes, best, solutions). Nodes = placements, best = deepest cell
    count reached (including the starting positions' tops), solutions = list
    of completed boards as tuples.
    """
    s = splitter
    nodes = best = 0
    sols = []
    for row, b in zip(rows, bases):
        placed = [int(x) for x in row]
        depth = max(i for i, x in enumerate(placed) if x >= 0)
        best = max(best, depth)
        used = {int(s.piece[x]) for x in placed[:depth] if s.piece[x] >= 0}
        while depth >= b:
            i = placed[depth] + 1
            while s.piece[i] >= 0 and int(s.piece[i]) in used:
                i += 1
            if s.piece[i] < 0:                       # list exhausted: backtrack
                placed[depth] = -1
                depth -= 1
                if depth >= 0 and s.piece[placed[depth]] >= 0:
                    used.discard(int(s.piece[placed[depth]]))
                continue
            placed[depth] = i
            nodes += 1
            used.add(int(s.piece[i]))
            depth += 1
            best = max(best, depth)
            if depth == s.n:                         # solution
                sols.append(tuple(placed))
                depth -= 1
                used.discard(int(s.piece[placed[depth]]))
                continue
            left = int(s.right[placed[depth - 1]])
            up = int(s.bottom[placed[depth - s.W]]) if depth >= s.W else 0
            f = int(s.flags[depth])
            placed[depth] = int(s.pre[((left*s.edgecount + up)*2 + (f >> 1))*2 + (f & 1)])
    return nodes, best, sols
