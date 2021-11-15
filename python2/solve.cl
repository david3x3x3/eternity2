// requirements:
// count nodes searched
// return number of solutions
// return max depth reached
// optional:
// return solutions found

#pragma OPENCL EXTENSION cl_khr_global_int32_base_atomics : enable

__constant short fit_table1[] = { PYFITTABLE1 };
__constant short fit_table2[][2] = { PYFITTABLE2 };

#define WIDTH KWIDTH
#define HEIGHT KHEIGHT
#define MEMTYPE KMEMTYPE
#define GLOBMEM KGLOBMEM
#define EDGECOUNT PYEDGECOUNT

//__constant short width = WIDTH, height = HEIGHT, edgecount = PYEDGECOUNT;
__constant short pieces[][4] = { PYPIECES };

__kernel void solve(int limit, __global short *search_data, __global int *nfound_data, __local short *lm_placed, __local unsigned char *lm_used,
		    __local short *lm_mindepth, __local short *lm_depth, __global int *res) {
  int gid = get_global_id(0), gsize = get_global_size(0);
  int lid = get_local_id(0), lsize = get_local_size(0);
  int i, j, k, nodes=0;
  int state = 0;
  local short *placed = 0;
  local unsigned char *used;
  
  used = lm_used+WIDTH*HEIGHT*lid;
  for(i=0;i<WIDTH*HEIGHT;i++) {
    used[i] = 0;
  }

  // search_data points to a 1-d array of int16s. the first gsize of
  // these shorts are the minimum search depth for that search. after
  // that, the current search state for each search is sent as a
  // width*height array of shorts. if the search is inactive, the
  // mindepth will be sent over as -1.
  
  // copy from global memory to local
  lm_mindepth[lid] = search_data[gid];
  placed = lm_placed+WIDTH*HEIGHT*lid;
  lm_depth[lid] = 0;
  if (lm_mindepth[lid] >= 0) {
    for(i=0; i<WIDTH*HEIGHT; i++) {
      placed[i] = search_data[gsize+WIDTH*HEIGHT*gid+i];
      j = placed[i];
      if (j < 0) {
	break;
      }
      lm_depth[lid] = i+1;
      used[fit_table2[j][0]]++;
    }
  } else {
    placed[0] = -1; // this will get filled in by a worker id to copy when we split
    used[0] = 0xf0; // this indicates we aren't searching
    state = 2;
  }

#define MAXSPLIT 16

  while (limit > 0 || state != 2) {
    //if (limit > 0 && limit % 10 == 0) {
    if (limit > 0) {
      // limit has to stay syncronized between all workers for barriers to work
      //if (gid == 0) { printf("barrier 1\n"); }
      barrier(CLK_LOCAL_MEM_FENCE);
      if (lid == 0) {
	// have lid #0 identify the work units to copy
	j = 0;
	k = WIDTH*HEIGHT;
	for(i=0; i<lsize; i++) {
	  if (lm_mindepth[i] >= 0) {
	    if (lm_depth[i] > lm_mindepth[i] &&
		lm_mindepth[i] < k &&
		lm_mindepth[i] < WIDTH*HEIGHT) {
	      // k is the minimum depth with workers to split
	      k = lm_mindepth[i];
	    }
	  } else {
	    lm_placed[WIDTH*HEIGHT*i] = -1;
	    lm_used[WIDTH*HEIGHT*i] = 0xf0;
	  }
	}
	//while(k < WIDTH*HEIGHT && j<lsize) {
	while(k < WIDTH*HEIGHT && j<MAXSPLIT) {
	  for(i=0; i<lsize; i++) {
	    if (lm_used[WIDTH*HEIGHT*i] < 0xf0 && 
		lm_depth[i] > lm_mindepth[i] &&
		lm_mindepth[i] == k) {
	      // copy source i identified

	      //for(;j<lsize;j++) {
	      for(;j<MAXSPLIT;j++) {
		if (lm_used[WIDTH*HEIGHT*j] == 0xf0) {
		  //if (gid<lsize) { printf("copy %d to %d\n", i, j); }
		  // copy dest j identified
		  lm_placed[WIDTH*HEIGHT*j] = i;
		  j++;
		  break;
		}
	      }
	      //if (j == lsize) {
	      if (j == MAXSPLIT) {
		break;
	      }
	    }
	  }
	  k++;
	}
	printf("j = %d\n", j);
      }
      //if (gid == 0) { printf("barrier 2\n"); }
      barrier(CLK_LOCAL_MEM_FENCE);
      if (1) {
	// do the copy (in parallel)
	if (used[0] == 0xf0) { // only splitters are running concurrently
	  j = placed[0];
	  if (j >= 0) {
	    printf("worker %d copying %d\n", lid, j);
	    lm_mindepth[lid] = lm_depth[lid] = lm_mindepth[j];
	    lm_mindepth[j]++;
	    for (i=0; i < WIDTH*HEIGHT; i++) {
	      placed[i] = lm_placed[WIDTH*HEIGHT*j+i];
	      used[i] = 0;
	    }
	    for (i=0; i <= lm_depth[lid]; i++) {
	      used[fit_table2[placed[i]][0]]++;
	    }
	    state = 1;
	  }
	}
      }
	
      //if (gid == 0) { printf("barrier 3\n"); }
      barrier(CLK_LOCAL_MEM_FENCE);
    }

    if (limit > 0) {
      limit--;
    }

    // use if instead of switch because state could change to next
    // state, and we don't want to skip activity in the loop if
    // possible
    if (state == 0) {
      if (lm_depth[lid]==WIDTH*HEIGHT) {
	lm_depth[lid]--;
	state++;
      } else {
	// set i to color to the left
	if (lm_depth[lid] > 0) {
	  k = placed[(lm_depth[lid]-1)];
	  i=pieces[fit_table2[k][0]][(5-fit_table2[k][1])&3];
	} else {
	  i=0;
	}
	// set j to color above
	if (lm_depth[lid]-WIDTH >= 0) {
	  k = placed[(lm_depth[lid]-WIDTH)];
	  j=pieces[fit_table2[k][0]][(6-fit_table2[k][1])&3];
	} else {
	  j=0;
	}
  	placed[lm_depth[lid]] = fit_table1[(i*EDGECOUNT+j)*4+
				   (lm_depth[lid] >= WIDTH*(HEIGHT-1))*2+
				   ((lm_depth[lid]+1)%WIDTH==0)];
	i=fit_table2[placed[lm_depth[lid]]][0];
	if (i == -1) {
	  state++; // can't add another piece
	} else {
	  used[i]++; // adding piece i
	  if (used[i] > 1) {
	    state++; // too many piece i
	  } else {
	    nodes++; // success!
	    if (limit == 0) {
	      state=2; //we've reached a stable position to stop
	    }
	    if(++lm_depth[lid] == WIDTH*HEIGHT) {
	      //printf("solved!\n");
	      atom_inc(nfound_data);
	    } else {
	      placed[lm_depth[lid]] = -1;
	    }
	  }
	}
      }
    }
    if (state == 1) {
      i = fit_table2[placed[lm_depth[lid]]++][0]; // incrementing position lm_depth[lid]
      used[i]--; // decreasing count for piece i
      i=fit_table2[placed[lm_depth[lid]]][0];
      //if (gid==0) { printf("try to replace with piece %d\n", i); }
      if (i == -1) {
	//if (gid==0) { printf("we have to back up\n"); }
	// we tried the last piece that will fit here
	if (--lm_depth[lid] < lm_mindepth[lid]) {
	  // if (gid==0) { printf("we've backed up past the start. we're done.\n"); }
	  // going back further completes the search
	  lm_mindepth[lid] = -1;
	  state++;
	}
      } else {
	// the next piece that fits here is not already used
	if (++used[i] < 2) {
	  //if (gid==0) { printf("piece %d is not used\n", used[i]); }
	  lm_depth[lid]++;
	  placed[lm_depth[lid]] = -1;
	  if (limit) {
	    state--;
	  } else {
	    state=2; //we've reached a stable position to stop
	  }
	  nodes++;
	} else {
	  //if (gid==0) { printf("piece %d is already used\n", used[i]); }
	}
      }
    }
  }

  if (lm_mindepth[lid] < 0) {
    lm_depth[lid]=0;
  }
  while (lm_depth[lid] < WIDTH*HEIGHT) {
    placed[lm_depth[lid]++] = -1;
  }

  // copy from local memory back to global
  search_data[gid] = lm_mindepth[lid];
  res[gid] = nodes;
  if (lm_mindepth[lid] >= 0) {
    for(i=0;i<WIDTH*HEIGHT;i++) {
      search_data[gsize+WIDTH*HEIGHT*gid+i] = placed[i];
      j = placed[i];
      /* if (j < 0) { */
      /* 	break; */
      /* } */
    }
  }
}
