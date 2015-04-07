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
