#pragma OPENCL EXTENSION cl_khr_global_int32_base_atomics : enable

__constant short fit_table1_c[] = { PYFITTABLE1 };
__constant short fit_table2_c[][2] = { PYFITTABLE2 };

#define WIDTH KWIDTH
#define HEIGHT KHEIGHT
#define MEMTYPE KMEMTYPE
#define GLOBMEM KGLOBMEM
#define FIT1_LEN (sizeof(fit_table1_c) / sizeof(fit_table1_c[0]))
#define FIT2_LEN (sizeof(fit_table2_c) / sizeof(fit_table2_c[0]))
#define NPIECES (sizeof(pieces_c) / sizeof(pieces_c[0]))

__constant short width = WIDTH, height = HEIGHT, edgecount = PYEDGECOUNT;
__constant short pieces_c[][4] = { PYPIECES };

// Used-piece bitmask, kept in registers.
#define USED(p) (((((p) < 64) ? used0 : used1) >> ((p) & 63)) & 1)
#define PIECE(e) ((int)((e) & 0xFF))
#define NO_PIECE 0xFF
#define FLIP(p) { if ((p) < 64) used0 ^= 1UL << (p); else used1 ^= 1UL << ((p) - 64); }

__kernel void mykernel(__global short* in_out, __global int* in_pos,
		       int max_pos, __global int* nassign,
		       __global short* found, __global int* nfound,
		       __global short *bases, int maxdepth, int limit,
		       __local short *localbuf, __global int *results,
		       __global short *g_best, __global ulong *depth_nodes) {
  int i;
  short best;
  int local_id = get_local_id(0);
  int global_id = get_global_id(0);
  int local_size = get_local_size(0);
  int group_id = get_group_id(0);
  MEMTYPE short *placed;

  // Copy the lookup tables to local memory. Every thread reads a different
  // entry, and divergent __constant reads are serialized on NVIDIA.
  // cand[] packs each fit_table2 entry with what the next cells need:
  // bits 0-7 piece (0xFF = end of list), bits 8-19 right color * edgecount * 4,
  // bits 20-31 bottom color * 4, i.e. the two fit_table1 index terms.
  // cell_flags[d] = fit_table1 index term for cell d (bottom row * 2 + right column).
  __local short fit_table1[FIT1_LEN];
  __local uint cand[FIT2_LEN];
  __local uchar cell_flags[WIDTH*HEIGHT];
  for (i = local_id; i < FIT1_LEN; i += local_size) {
    fit_table1[i] = fit_table1_c[i] - 1;   // stored as "one before the first candidate"
  }
  for (i = local_id; i < FIT2_LEN; i += local_size) {
    short p = fit_table2_c[i][0], r = fit_table2_c[i][1];
    cand[i] = p < 0 ? 0xFF :
      (uint)p | ((uint)(pieces_c[p][(5-r)&3] * edgecount * 4) << 8) | ((uint)(pieces_c[p][(6-r)&3] * 4) << 20);
  }
  for (i = local_id; i < WIDTH*HEIGHT; i += local_size) {
    cell_flags[i] = (i >= WIDTH*(HEIGHT-1))*2 + ((i+1)%WIDTH==0);
  }
  barrier(CLK_LOCAL_MEM_FENCE);

  if(in_pos[global_id] < 0) {
    results[global_id] = 0;
    return;
  }

  placed = localbuf + local_id*width*height;
  for(i=0;i<width*height;i++) {
    placed[i] = in_out[in_pos[global_id]*width*height+i];
  }
  // each position has its own base: it's done when the search backtracks above it
  int mindepth = bases[in_pos[global_id]];

  int j,k,depth=-1;
  long res=0;
  // Invariant: the mask holds the pieces at placed[0..depth-1]; the candidate
  // at placed[depth] is never in it.
  ulong used0 = 0, used1 = 0;

  for (i=0;i<width*height;i++) {
    if (placed[i] >= 0) {
      best = depth = i;
    }
  }
  for (i=0;i<depth;i++) {
    k = placed[i];
    if (k > 0) {
      j = PIECE(cand[k]);
      if (j != NO_PIECE) FLIP(j);
    }
  }

  while (1) {
    if (depth < mindepth) {
      for(i=0;i<width*height;i++) {
	in_out[in_pos[global_id]*width*height+i] = placed[i];
      }
      i = atomic_inc(nassign);
      if (i >= max_pos) {
	in_pos[global_id] = -1;
	break;
      }
      in_pos[global_id] = i;
      mindepth = bases[i];
      for(i=0;i<width*height;i++) {
	placed[i] = in_out[in_pos[global_id]*width*height+i];
      }

      // this is a repeat of the previous code; probably should be a separate function
      for (i=0;i<width*height;i++) {
	if (placed[i] > 0) {
	  depth = i;
	}
      }
      used0 = used1 = 0;
      for (i=0;i<depth;i++) {
	k = placed[i];
	if (k > 0) {
	  j = PIECE(cand[k]);
	  if (j != NO_PIECE) FLIP(j);
	}
      }
    }

    // advance to the next candidate whose piece isn't used elsewhere
    i = placed[depth];
    do {
      j = PIECE(cand[++i]);
    } while (j != NO_PIECE && USED(j));
    placed[depth] = i;
    if (j == NO_PIECE) {
      placed[depth] = -1;
      depth--;
      // backtrack: the piece at the new depth becomes the current candidate
      if (depth >= 0) {
	j = PIECE(cand[placed[depth]]);
	if (j != NO_PIECE) FLIP(j);
      }
      continue;
    }

    if (res++ >= limit) {
      --placed[depth];
      --res;
      break;
    }

#ifdef DEPTH_STATS
    // per-worker histogram of placements by cell (only with --depth-stats)
    depth_nodes[global_id*WIDTH*HEIGHT + depth]++;
#endif
    FLIP(j);
    if(++depth > best) {
      best = depth;
    }

    if(depth < width*height) {
      i = (cand[placed[depth-1]] >> 8) & 0xFFF;                // right color of left neighbor
      j = depth >= WIDTH ? cand[placed[depth-WIDTH]] >> 20 : 0;  // bottom color of piece above
      placed[depth] = fit_table1[i + j + cell_flags[depth]];
    } else {
      // record the solution
      j = atomic_inc(nfound);
      for(i=0;i<width*height;i++) {
	found[j*width*height+i] = placed[i];
      }
      depth--;
      j = PIECE(cand[placed[depth]]);
      FLIP(j);
    }
  }

  results[global_id] = res;
  g_best[global_id] = best;

  if(in_pos[global_id] >= 0) {
    for(i=0;i<width*height;i++) {
      in_out[in_pos[global_id]*width*height+i] = placed[i];
    }
  }
}
