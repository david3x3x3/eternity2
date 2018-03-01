__constant short fit_table1[] = { PYFITTABLE1 };
__constant short fit_table2[][2] = { PYFITTABLE2 };

#define WIDTH KWIDTH
#define HEIGHT KHEIGHT
#define MEMTYPE KMEMTYPE
#define GLOBMEM KGLOBMEM

__constant short width = WIDTH, height = HEIGHT, edgecount = PYEDGECOUNT;
__constant short pieces[][4] = { PYPIECES };

long mysearch(MEMTYPE short *placed, int mindepth, int limit) {
  int i,j,k,depth=-1;
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

  while (depth >= mindepth) {
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
      return --res;
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
      return res;
    }
  }
  
  return res;
}

__kernel void mykernel(__global short* in_out, int mindepth, int maxdepth, int limit, __local short *localbuf, __global int *results) {
  int i,local_id, global_id;
  MEMTYPE short *memptr;
  
  global_id = get_global_id(0);
#if GLOBMEM == 0
  local_id = get_local_id(0);
  for(i=0;i<width*height;i++) {
    localbuf[local_id*width*height+i] = in_out[global_id*width*height+i];
  }
  memptr = localbuf + local_id*width*height;
#else
  memptr = in_out+global_id*width*height;
#endif
  results[global_id] = mysearch(memptr, mindepth, limit);

#if GLOBMEM == 0
  for(i=0;i<width*height;i++) {
    in_out[global_id*width*height+i] = localbuf[local_id*width*height+i];
  }
#endif
}
