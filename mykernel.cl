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
  results[global_id] = mysearch(memptr, mindepth, maxdepth, 2, -1, limit);
#if GLOBMEM == 0
  for(i=0;i<width*height;i++) {
    in_out[global_id*width*height+i] = localbuf[local_id*width*height+i];
  }
#endif
}
