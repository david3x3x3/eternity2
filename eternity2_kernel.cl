#define MYKERNEL 1

#ifdef MYKERNEL
FITTABLE;
#define WIDTH KWIDTH
#define HEIGHT KHEIGHT
#endif

long mysearch(
#ifdef MYKERNEL
local
#endif
short *placed, int mindepth, int maxdepth, int doprint, int numbered, int limit) {
  int row,col,i,j,k,down,right,depth=-1,dup_check_count;
  long res=0;
#ifdef MYKERNEL
  int placed2[WIDTH*HEIGHT], solcount=0;
#endif

  for (i=0;i<width*height;i++) {
    placed2[i] = 0;
    if (placed[i] > 0) {
      depth = i;
    }
  }
  for (i=0;i<=depth;i++) {
    if (placed[i] > 0) {
      j = fit_table2[placed[i]];
      if (j >= 0) {
	placed2[j/4]++;
      }
    }
  }
  

  while (depth >= mindepth) {
    i = placed[depth];

    if (fit_table2[i] >= 0) {
      placed2[fit_table2[i]/4]--;
    }
    i = ++placed[depth];
    if (fit_table2[i] == -1) {
      placed[depth] = 0;
      depth--;
      continue;
    }

    int ii = fit_table2[i]/4;

    if (++placed2[ii] > 1) {
      continue;
    }

    /* if(doprint==2) { */
    /*   printf("depth %d - ", depth+1); */
    /*   for(i=0;i<width*height;i++) { */
    /* 	printf("%d%c", placed2[i], (i+1)%5?' ':'/'); */
    /*   } */
    /*   printf("\n"); */
    /* } */

    if (width==height && depth == 0 && ii != 0) {
      continue;
    }

    if (res++ >= limit) {
      --placed[depth];
      return --res;
    }
		   
    depth++;

    /* if(doprint==2) { */
    /*   print_solution(placed, depth, 1); */
    /* } */
    
    if (depth==maxdepth && numbered != -2 && (numbered < 0 || numbered != solcount)) {
      solcount++;
      if (doprint) {
	//if(doprint==2) printf("return 2 (%d,%d)\n", numbered, solcount);
	return res;
      }
      depth--;
    } else {
      row = depth/width;
      col = depth%width;
      down = 0;
      right = 0;
      if (col) {
	k=fit_table2[placed[(depth-1)]];
	i=pieces[k/4][(5-k%4)%4];
	if (col == width-1) {
	  right=1;
	}
      } else {
	i=0;
      }
      if (row) {
	k=fit_table2[placed[(depth-width)]];
	j=pieces[k/4][(6-k%4)%4];
	if (row == height-1) {
	  down=1;
	}
      } else {
	j=0;
      }
      /* if(doprint == 2) { */
      /* 	printf("left, up is %d, %d\n", i, j); */
      /* } */
      placed[depth] = fit_table1[(i*edgecount+j)*4+down*2+right]-1;

      if (depth==maxdepth) {
	solcount++;
	//if(doprint==2) printf("return 3\n");
	return (numbered == -2) ? res : 0; // special case for setting up numbered solutions
      }
    }
  }

  return res;
}

__kernel void mykernel(__global short* in_out, int mindepth, int maxdepth, int limit, __local short *localbuf, __global int *results) {
  int i,local_id, global_id;
  
  local_id = get_local_id(0);
  global_id = get_global_id(0);
  for(i=0;i<width*height;i++) {
    localbuf[local_id*width*height+i] = in_out[global_id*width*height+i];
  }
  results[global_id] = mysearch(localbuf + local_id*width*height, mindepth, maxdepth, 2, -1, limit);
  for(i=0;i<width*height;i++) {
    in_out[global_id*width*height+i] = localbuf[local_id*width*height+i];
  }
}
