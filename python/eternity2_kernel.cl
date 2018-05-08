#pragma OPENCL EXTENSION cl_khr_global_int32_base_atomics : enable

__constant short fit_table1[] = { PYFITTABLE1 };
__constant short fit_table2[][2] = { PYFITTABLE2 };

#define WIDTH KWIDTH
#define HEIGHT KHEIGHT
#define MEMTYPE KMEMTYPE
#define GLOBMEM KGLOBMEM

__constant short width = WIDTH, height = HEIGHT, edgecount = PYEDGECOUNT;
__constant short pieces[][4] = { PYPIECES };

__kernel void mykernel(__global short* in_out, __global int* in_pos,
		       int max_pos, __global int* nassign,
		       __global short* found, __global int* nfound,
		       int mindepth, int maxdepth, int limit,
		       __local short *localbuf, __global int *results) {
  int i,local_id, global_id;
  MEMTYPE short *placed;
  
  // i = atomic_inc(nfound);

  global_id = get_global_id(0);

  if(in_pos[global_id] < 0) {
    results[global_id] = 0;
    return;
  }
  
  local_id = get_local_id(0);

  placed = localbuf + local_id*width*height;
  for(i=0;i<width*height;i++) {
    placed[i] = in_out[in_pos[global_id]*width*height+i];
  }

  /* results[global_id] = mysearch(placed, mindepth, limit, in_pos, max_pos, */
  /* 				found, nfound); */

  int j,k,depth=-1;
  long res=0;
  short placed2[WIDTH*HEIGHT];

  for (i=0;i<width*height;i++) {
    placed2[i] = 0;
    if (placed[i] > 0) {
      depth = i;
    }
  }
  for (i=0;i<=depth;i++) {
    k = placed[i];
    if (k > 0) {
      j = fit_table2[k][0];
      if (j >= 0) {
	placed2[j]++;
      }
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
      for(i=0;i<width*height;i++) {
	placed[i] = in_out[in_pos[global_id]*width*height+i];
      }

      // this is a repeat of the previous code; probably should be a separate function
      for (i=0;i<width*height;i++) {
	placed2[i] = 0;
	if (placed[i] > 0) {
	  depth = i;
	}
      }
      for (i=0;i<=depth;i++) {
	k = placed[i];
	if (k > 0) {
	  j = fit_table2[k][0];
	  if (j >= 0) {
	    placed2[j]++;
	  }
	}
      }

    }
    
    i = placed[depth];

    j = fit_table2[i][0];
    if (j >= 0) {
      placed2[j]--;
    }
    i = ++placed[depth];
    if (fit_table2[i][0] == -1) {
      placed[depth] = 0;
      depth--;
      continue;
    }

    if (++placed2[fit_table2[i][0]] > 1) {
      continue;
    }

    if (res++ >= limit) {
      --placed[depth];
      --res;
      break;
    }
		   
    depth++;

    if(depth < width*height) {
      k = placed[(depth-1)];
      i=pieces[fit_table2[k][0]][(5-fit_table2[k][1])&3];

      k = placed[(depth-width)];
      j=pieces[fit_table2[k][0]][(6-fit_table2[k][1])&3];

      placed[depth] = fit_table1[(i*edgecount+j)*4+
				 (depth >= WIDTH*(HEIGHT-1))*2+
				 ((depth+1)%width==0)]-1;
    } else {
      // record the solution
      j = atomic_inc(nfound);
      for(i=0;i<width*height;i++) {
	found[j*width*height+i] = placed[i];
      }
      depth--;
    }
  }

  results[global_id] = res;
  
  for(i=0;i<width*height;i++) {
    in_out[in_pos[global_id]*width*height+i] = placed[i];
  }
}
