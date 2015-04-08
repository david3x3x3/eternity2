#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <time.h>

#ifdef MAC
#include <OpenCL/cl.h>
#else  
#include <CL/cl.h>
#endif

typedef struct {
  const char *name;
  int width;
  int height;
  int (*pieces)[4];
} puzinfo;

int (*pieces)[4];

int width, height;

int *fit_table0, *fit_table1, *fit_table2, fit_table2_size;
char *fit_table_buffer;
int edgecount=0;
int piececount,*placed2;
int best=0;
int ft_cols=15;
int quiet=0, usecpu=0, maxwgs=0, maxcu=0;

cl_program program;
cl_kernel kernel;
cl_platform_id platform;
cl_device_id device;
cl_context context;
cl_command_queue queue;
size_t max_workgroup_size, total_work_units;
time_t start_time;

#include "pieces.h"

void
clerror(int err, char *msg) {
  char *c = NULL;
  if(!err) {
    return;
  }
  switch(err) {
  case CL_SUCCESS: c = "CL_SUCCESS"; break;
  case CL_DEVICE_NOT_FOUND: c = "CL_DEVICE_NOT_FOUND"; break;
  case CL_DEVICE_NOT_AVAILABLE: c = "CL_DEVICE_NOT_AVAILABLE"; break;
  case CL_COMPILER_NOT_AVAILABLE: c = "CL_COMPILER_NOT_AVAILABLE"; break;
  case CL_MEM_OBJECT_ALLOCATION_FAILURE: c = "CL_MEM_OBJECT_ALLOCATION_FAILURE"; break;
  case CL_OUT_OF_RESOURCES: c = "CL_OUT_OF_RESOURCES"; break;
  case CL_OUT_OF_HOST_MEMORY: c = "CL_OUT_OF_HOST_MEMORY"; break;
  case CL_PROFILING_INFO_NOT_AVAILABLE: c = "CL_PROFILING_INFO_NOT_AVAILABLE"; break;
  case CL_MEM_COPY_OVERLAP: c = "CL_MEM_COPY_OVERLAP"; break;
  case CL_IMAGE_FORMAT_MISMATCH: c = "CL_IMAGE_FORMAT_MISMATCH"; break;
  case CL_IMAGE_FORMAT_NOT_SUPPORTED: c = "CL_IMAGE_FORMAT_NOT_SUPPORTED"; break;
  case CL_BUILD_PROGRAM_FAILURE: c = "CL_BUILD_PROGRAM_FAILURE"; break;
  case CL_MAP_FAILURE: c = "CL_MAP_FAILURE"; break;
  case CL_MISALIGNED_SUB_BUFFER_OFFSET: c = "CL_MISALIGNED_SUB_BUFFER_OFFSET"; break;
  case CL_EXEC_STATUS_ERROR_FOR_EVENTS_IN_WAIT_LIST: c = "CL_EXEC_STATUS_ERROR_FOR_EVENTS_IN_WAIT_LIST"; break;
  case CL_COMPILE_PROGRAM_FAILURE: c = "CL_COMPILE_PROGRAM_FAILURE"; break;
  case CL_LINKER_NOT_AVAILABLE: c = "CL_LINKER_NOT_AVAILABLE"; break;
  case CL_LINK_PROGRAM_FAILURE: c = "CL_LINK_PROGRAM_FAILURE"; break;
  case CL_DEVICE_PARTITION_FAILED: c = "CL_DEVICE_PARTITION_FAILED"; break;
  case CL_KERNEL_ARG_INFO_NOT_AVAILABLE: c = "CL_KERNEL_ARG_INFO_NOT_AVAILABLE"; break;
  case CL_INVALID_VALUE: c = "CL_INVALID_VALUE"; break;
  case CL_INVALID_DEVICE_TYPE: c = "CL_INVALID_DEVICE_TYPE"; break;
  case CL_INVALID_PLATFORM: c = "CL_INVALID_PLATFORM"; break;
  case CL_INVALID_DEVICE: c = "CL_INVALID_DEVICE"; break;
  case CL_INVALID_CONTEXT: c = "CL_INVALID_CONTEXT"; break;
  case CL_INVALID_QUEUE_PROPERTIES: c = "CL_INVALID_QUEUE_PROPERTIES"; break;
  case CL_INVALID_COMMAND_QUEUE: c = "CL_INVALID_COMMAND_QUEUE"; break;
  case CL_INVALID_HOST_PTR: c = "CL_INVALID_HOST_PTR"; break;
  case CL_INVALID_MEM_OBJECT: c = "CL_INVALID_MEM_OBJECT"; break;
  case CL_INVALID_IMAGE_FORMAT_DESCRIPTOR: c = "CL_INVALID_IMAGE_FORMAT_DESCRIPTOR"; break;
  case CL_INVALID_IMAGE_SIZE: c = "CL_INVALID_IMAGE_SIZE"; break;
  case CL_INVALID_SAMPLER: c = "CL_INVALID_SAMPLER"; break;
  case CL_INVALID_BINARY: c = "CL_INVALID_BINARY"; break;
  case CL_INVALID_BUILD_OPTIONS: c = "CL_INVALID_BUILD_OPTIONS"; break;
  case CL_INVALID_PROGRAM: c = "CL_INVALID_PROGRAM"; break;
  case CL_INVALID_PROGRAM_EXECUTABLE: c = "CL_INVALID_PROGRAM_EXECUTABLE"; break;
  case CL_INVALID_KERNEL_NAME: c = "CL_INVALID_KERNEL_NAME"; break;
  case CL_INVALID_KERNEL_DEFINITION: c = "CL_INVALID_KERNEL_DEFINITION"; break;
  case CL_INVALID_KERNEL: c = "CL_INVALID_KERNEL"; break;
  case CL_INVALID_ARG_INDEX: c = "CL_INVALID_ARG_INDEX"; break;
  case CL_INVALID_ARG_VALUE: c = "CL_INVALID_ARG_VALUE"; break;
  case CL_INVALID_ARG_SIZE: c = "CL_INVALID_ARG_SIZE"; break;
  case CL_INVALID_KERNEL_ARGS: c = "CL_INVALID_KERNEL_ARGS"; break;
  case CL_INVALID_WORK_DIMENSION: c = "CL_INVALID_WORK_DIMENSION"; break;
  case CL_INVALID_WORK_GROUP_SIZE: c = "CL_INVALID_WORK_GROUP_SIZE"; break;
  case CL_INVALID_WORK_ITEM_SIZE: c = "CL_INVALID_WORK_ITEM_SIZE"; break;
  case CL_INVALID_GLOBAL_OFFSET: c = "CL_INVALID_GLOBAL_OFFSET"; break;
  case CL_INVALID_EVENT_WAIT_LIST: c = "CL_INVALID_EVENT_WAIT_LIST"; break;
  case CL_INVALID_EVENT: c = "CL_INVALID_EVENT"; break;
  case CL_INVALID_OPERATION: c = "CL_INVALID_OPERATION"; break;
  case CL_INVALID_GL_OBJECT: c = "CL_INVALID_GL_OBJECT"; break;
  case CL_INVALID_BUFFER_SIZE: c = "CL_INVALID_BUFFER_SIZE"; break;
  case CL_INVALID_MIP_LEVEL: c = "CL_INVALID_MIP_LEVEL"; break;
  case CL_INVALID_GLOBAL_WORK_SIZE: c = "CL_INVALID_GLOBAL_WORK_SIZE"; break;
  case CL_INVALID_PROPERTY: c = "CL_INVALID_PROPERTY"; break;
  case CL_INVALID_IMAGE_DESCRIPTOR: c = "CL_INVALID_IMAGE_DESCRIPTOR"; break;
  case CL_INVALID_COMPILER_OPTIONS: c = "CL_INVALID_COMPILER_OPTIONS"; break;
  case CL_INVALID_LINKER_OPTIONS: c = "CL_INVALID_LINKER_OPTIONS"; break;
  case CL_INVALID_DEVICE_PARTITION_COUNT: c = "CL_INVALID_DEVICE_PARTITION_COUNT"; break;
    //  case CL_INVALID_PIPE_SIZE: c = "CL_INVALID_PIPE_SIZE"; break;
    //  case CL_INVALID_DEVICE_QUEUE: c = "CL_INVALID_DEVICE_QUEUE"; break;
  }
  if(c) {
    printf("%s: %s\n", msg, c);
  } else {
    printf("%s: code %d\n", msg, err);
  }
}


void
init() {
  int i,j,k,m,down,right,maxm=0;
  char *c;

  c = fit_table_buffer = malloc(200000);
  c[0] = '\0';

  // build the fit_table
  piececount = width*height;
  placed2=malloc(piececount*sizeof(int));
  for (i=0;i<width*height;i++) {
    for (j=0;j<4;j++) {
      if (pieces[i][j]+1 > edgecount) {
	edgecount = pieces[i][j]+1;
      }
    }
  }
  printf("edgecount = %d\n",edgecount);
  fit_table0 = malloc(edgecount*edgecount*4*ft_cols*sizeof(int));

  for (i=0;i<edgecount*edgecount*4;i++) {
    fit_table0[i*ft_cols]=-1;
  }
  for (i=0;i<piececount;i++) {
    for (j=0;j<4;j++) {
      down = pieces[i][(j+3)%4] == 0;
      right = pieces[i][(j+2)%4] == 0;
      k = (pieces[i][j]*edgecount+pieces[i][(j+1)%4])*4+down*2+right;
      //printf("piece %d/%d (%d) goes in %d\n", i+1, 3-j, i*4+3-j, k);
      for (m=0; fit_table0[k*ft_cols+m] != -1; m++) {
	;
      }
      fit_table0[k*ft_cols+m] = i*4+3-j;
      fit_table0[k*ft_cols+m+1] = -1;
      if (m+2 > maxm) {
	maxm = m+2;
      }
    }
  }
  printf("maxm = %d\n", maxm);

  fit_table2_size=3;
  // calculate fit_table2 size
  for (i=0; i<edgecount*edgecount*4;i++) {
    if(fit_table0[i*ft_cols] != -1) {
      for (j=0; j<maxm; j++) {
	fit_table2_size++;
	if(fit_table0[i*ft_cols+j] == -1) {
	  break;
	}
      }
    }
  }
  //printf("fit_table2_size = %d\n", fit_table2_size);
  // fill in fit_table1 and fit_table2
  fit_table1 = malloc(edgecount*edgecount*4*sizeof(int));
  fit_table2 = malloc(fit_table2_size*sizeof(int));
  fit_table2[0] = fit_table2[1] = fit_table2[2] = -1;
  fit_table2_size=3;
  for (i=0; i<edgecount*edgecount*4;i++) {
    //sprintf(c, "%s{", i==0?"":",");
    //c += strlen(c);
    if(fit_table0[i*ft_cols] != -1) {
      fit_table1[i] = fit_table2_size;
      for (j=0; j<maxm; j++) {
	fit_table2[fit_table2_size++] = fit_table0[i*ft_cols+j];
	if(fit_table0[i*ft_cols+j] == -1) {
	  break;
	}
      }
    } else {
      fit_table1[i] = 2;
    }
  }
  //printf("fit_table2_size = %d\n", fit_table2_size);

  // format fit_table1 and fit_table2 for kernel
  sprintf(c, "__constant int width=%d, height=%d, edgecount=%d, ft_cols=%d, fit_table1[] = {", width, height, edgecount, maxm); //, edgecount*edgecount*4*maxm);
  c += strlen(c);

  for (i=0; i<edgecount*edgecount*4;i++) {
    if (i%30 == 0) {
      sprintf(c, "\n");
      c += strlen(c);
    }
    k=fit_table1[i];
    sprintf(c, "%s%d", i==0?"":",", k);
    c += strlen(c);
  }

  sprintf(c, "}, fit_table2[] = {");
  c += strlen(c);

  for (i=0; i<fit_table2_size;i++) {
    if (i%30 == 0) {
      sprintf(c, "\n");
      c += strlen(c);
    }
    k=fit_table2[i];
    sprintf(c, "%s%d", i==0?"":",", k);
    c += strlen(c);
  }

  sprintf(c, "}, pieces[][4] = {");
  c += strlen(c);
  for (i=0;i<piececount;i++) {
    if (!(i%8)) {
      sprintf(c, "\n");
      c += strlen(c);
    }
    sprintf(c, "{%d,%d,%d,%d},",
	    pieces[i][0],
	    pieces[i][1],
	    pieces[i][2],
	    pieces[i][3]);
    c += strlen(c);
  }
  sprintf(c, "}");
  c += strlen(c);

  printf("table_size = %zu\n", strlen(fit_table_buffer)+1);
}

cl_short *clplaced;
long solcount = 0, clsolcount=0;

void print_solution(
#ifdef MYKERNEL
global
#endif
short *placed, int depth, int count) {
  int k, ii;
  printf("solution %d: ", count);
  for (k=0;k<depth;k++) {
    ii = placed[k];
    /* if (k%width == 0) { */
    /*   printf("\n"); */
    /* } */
    if (ii && fit_table2[ii] > 0) {
      printf("%d/%d ", fit_table2[ii]/4+1, fit_table2[ii]%4);
    } else {
      printf("-1 ");
    }
  }
  printf("\n");
}

void print_solution_martin(
#ifdef MYKERNEL
global
#endif
			   short *placed, int depth, int count) {
  int k, ii;
  printf("%07d-", count-1);
  for (k=0;k<depth;k++) {
    ii = placed[k];
    if (ii && fit_table2[ii] >= 0) {
      printf("%02d", fit_table2[ii]/4);
    } else {
      printf("-1 ");
    }
  }
  printf("\n");
}

void print_solution_debug(
#ifdef MYKERNEL
local
#endif
			   short *placed, int depth, int count) {
  int k, ii;
  printf("%07d-", count-1);
  for (k=0;k<depth;k++) {
    ii = placed[k];
    /* if (k%width == 0) { */
    /*   printf("\n"); */
    /* } */
    printf("%d ", ii);
  }
  printf("\n");
}

// BEGIN_KERNEL

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
  int row,col,i,j,k,down,right,depth=-1;
  long res=0;
#ifdef MYKERNEL
  int placed2[WIDTH*HEIGHT], solcount=0;
#endif

  for (i=0;i<width*height;i++) {
    placed2[i] = 0;
    if (placed[i] > 0) {
      //printf("%d ", placed[i]);
      depth = i;
    }
  }
  //printf("\n");
  for (i=0;i<=depth;i++) {
    if (placed[i] > 0) {
      j = fit_table2[placed[i]];
      if (j >= 0) {
	placed2[j/4]++;
      }
    }
  }
  
  //printf("depth = %d\n", depth);

  while (depth >= mindepth) {
    //if(doprint==2) printf("depth = %d\n", depth);
    i = placed[depth];

    //printf("i=%d, j=%d\n", i, j);
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
    //int jj = fit_table0[i*ft_cols+j]%4;
    // printf("trying %d/%d at %d\n", ii, jj, depth);

    // check for dups
    if (++placed2[ii] > 1) {
      //skipping dup
      continue;
    }

    /* if(doprint==2) { */
    /*   printf("depth %d - ", depth+1); */
    /*   for(i=0;i<width*height;i++) { */
    /* 	printf("%d%c", placed2[i], (i+1)%5?' ':'/'); */
    /*   } */
    /*   printf("\n"); */
    /* } */

    // skipped mirrored solutions
    if (width==height && depth == 0 && ii != 0) {
      continue;
    }

    // count nodes
    if (res++ >= limit) {
      --placed[depth];
      //if(doprint==2) printf("return 1\n");
      return --res;
    }
		   
    depth++;

    /* if(doprint==2) { */
    /*   print_solution(placed, depth, 1); */
    /* } */
    
    //    if (depth>best) {
    //      best = depth;
    //    }
    if (depth==maxdepth && numbered != -2 && (numbered < 0 || numbered != solcount)) {
      //found solution
      solcount++;
      if (doprint) {
	//if(doprint==2) printf("return 2 (%d,%d)\n", numbered, solcount);
	return res;
      }
      //count solutions
      //res++;
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

  //if(doprint==2) printf("return 4\n");
  return res;
}

// END_KERNEL

char *mysub(char *src, char *pat, char *with) {
  char *s1, *dest;

  dest = malloc(strlen(src)+strlen(with)-strlen(pat)+1);
  s1 = strstr(src, pat);
  s1[0] = '\0';
  s1 += strlen(pat);
  sprintf(dest, "%s%s%s", src, with, s1);
  free(src);
  return(dest);
}

int clinit() {
   /* Host/device data structures */
  cl_int i, j, err;

   /* Program/kernel data structures */
   FILE *program_handle;
   char *program_buffer, *program_log, small_buff[32];
   size_t program_size, log_size;
   
   /* Data and buffers */

   /* Identify a platform */
   err = clGetPlatformIDs(1, &platform, NULL);
   if (err < 0) {
     clerror(err, "Couldn't find any platforms");
     exit(1);
   }

   /* Access a device */
   err = clGetDeviceIDs(platform, usecpu ? CL_DEVICE_TYPE_CPU : CL_DEVICE_TYPE_GPU, 1, &device, NULL);
   if (err < 0) {
     clerror(err,"Couldn't find any devices");
     exit(1);
   }

   /* Create the context */
   context = clCreateContext(NULL, 1, &device, NULL, NULL, &err);
   if (err < 0) {
     clerror(err,"Couldn't create a context");
     exit(1);
   }

   /* Read program file and place content into buffer */
   program_handle = fopen("eternity2_kernel.cl", "r");
   if (program_handle == NULL) {
     clerror(err,"Couldn't find the program file");
     exit(1);   
   }
   fseek(program_handle, 0, SEEK_END);
   program_size = ftell(program_handle);
   rewind(program_handle);
   program_buffer = (char*)malloc(program_size + 1);
   program_buffer[program_size] = '\0';
   fread(program_buffer, sizeof(char), program_size, program_handle);
   fclose(program_handle);

   sprintf(small_buff, "%d", width);
   program_buffer = mysub(program_buffer, "KWIDTH", small_buff);
   sprintf(small_buff, "%d", height);
   program_buffer = mysub(program_buffer, "KHEIGHT", small_buff);
   program_buffer = mysub(program_buffer, "FITTABLE", fit_table_buffer);
   program_size = strlen(program_buffer);

   FILE *fp = fopen("debug.cl","w");
   fprintf(fp,"%s",program_buffer);
   fclose(fp);
   //printf("program_buffer = %s\n", program_buffer);

   /* Create program from file */
   program = clCreateProgramWithSource(context, 1, 
      (const char**)&program_buffer, &program_size, &err);
   if (err < 0) {
     clerror(err,"Couldn't create the program");
     exit(1);
   }
   free(program_buffer);

   /* Build program */
   err = clBuildProgram(program, 0, NULL, NULL, NULL, NULL);
   printf("err = %d\n", err);
   if (err < 0) {

      /* Find size of log and print to std output */
      clGetProgramBuildInfo(program, device, CL_PROGRAM_BUILD_LOG, 
            0, NULL, &log_size);
      program_log = (char*) malloc(log_size + 1);
      program_log[log_size] = '\0';
      clGetProgramBuildInfo(program, device, CL_PROGRAM_BUILD_LOG, 
            log_size + 1, program_log, NULL);
      printf("%s\n", program_log);
      free(program_log);
      exit(1);
   }

   kernel = clCreateKernel(program, "mykernel", &err);
   if (err < 0) {
      perror("Couldn't create the kernel");
      exit(1);   
   }

   /* Create a CL command queue for the device*/
   //printf("calling clCreateCommandQueue\n");
   queue = clCreateCommandQueue(context, device, 0, &err);
   if (err < 0) {
     perror("Couldn't create the command queue");
     exit(1);
   }

   err = clGetDeviceInfo(device, CL_DEVICE_MAX_WORK_GROUP_SIZE, sizeof(size_t), &max_workgroup_size, NULL);
   //max_workgroup_size = 256;
   if(maxwgs && maxwgs < max_workgroup_size) {
     max_workgroup_size = maxwgs;
   }
   printf("max_workgroup_size = %zu\n", max_workgroup_size);

   cl_ulong local_mem_size;
   err = clGetDeviceInfo(device, CL_DEVICE_LOCAL_MEM_SIZE, sizeof(cl_ulong), &local_mem_size, NULL);
   if (err < 0) {
     clerror(err, "clGetDeviceInfo (local_mem_size)");
     exit(1);
   }
   printf("local_mem_size = %ld\n", local_mem_size);

   size_t preferred_work_group_size_multiple;
   err = clGetKernelWorkGroupInfo(kernel, device, CL_KERNEL_PREFERRED_WORK_GROUP_SIZE_MULTIPLE, sizeof(size_t),
				  &preferred_work_group_size_multiple, NULL);
   if (err < 0) {
     clerror(err, "clGetKernelWorkGroupInfo (preferred_work_group_size_multiple)");
     exit(1);
   }
   printf("preferred_work_group_size_multiple = %zu\n", preferred_work_group_size_multiple);

   cl_ulong kernel_local_mem_size;
   err = clGetKernelWorkGroupInfo(kernel, device, CL_KERNEL_LOCAL_MEM_SIZE, sizeof(cl_ulong),
				  &kernel_local_mem_size, NULL);
   if (err < 0) {
     clerror(err, "clGetKernelWorkGroupInfo (kernel_local_mem_size)");
     exit(1);
   }
   printf("kernel_local_mem_size = %ld\n", kernel_local_mem_size);

   printf("solvers per workgroup (memory limit) = %ld\n", local_mem_size/(piececount*sizeof(cl_short)));

   if(local_mem_size/(piececount*sizeof(cl_short)) < max_workgroup_size) {
     // shrink workgroup size if necessary because of local memory requirements
     max_workgroup_size = local_mem_size/(piececount*sizeof(cl_short));
   }

   if(max_workgroup_size / preferred_work_group_size_multiple > 0) {
     // make sure workgroup size is a preferred multiple
     // i'm not sure this helps.
     // max_workgroup_size -= max_workgroup_size % preferred_work_group_size_multiple;
   }

   printf("workgroup size = %zu\n", max_workgroup_size);
   
   cl_uint max_compute_units;
   err = clGetDeviceInfo(device, CL_DEVICE_MAX_COMPUTE_UNITS, sizeof(cl_uint), &max_compute_units, NULL);

   if(maxcu && maxcu < max_compute_units) {
     max_compute_units = maxcu;
   }

   printf("max_compute_units = %d\n", max_compute_units);

   total_work_units = max_compute_units * max_workgroup_size;
   printf("total_work_units = %zu\n", total_work_units);

   clplaced = malloc(total_work_units*piececount*sizeof(cl_short));
   for(i=0;i<total_work_units;i++) {
     for(j=0;j<piececount;j++) {
       clplaced[i*piececount+j] = 0;
     }
   }

   return 0;
}

int
clsearch(cl_int depth, cl_int limit) {
  cl_int err, clplaced_size=total_work_units*piececount*sizeof(cl_short);
  cl_event kernel_event;
  int *result = malloc(total_work_units*sizeof(cl_int));
  int nodes=0, i;

  //printf("clsearch(depth=%d,limit=%d,clplaced_size=%d)\n", depth, limit, clplaced_size);

  //printf("calling clCreateBuffer\n");
  /* Create CL buffers to hold input and output data */
  cl_mem piece_buff = clCreateBuffer(context, CL_MEM_READ_WRITE |
			      CL_MEM_COPY_HOST_PTR, clplaced_size, clplaced, &err);
  clerror(err,"Couldn't create a buffer object");

  cl_mem res_buff = clCreateBuffer(context, CL_MEM_WRITE_ONLY,
				   total_work_units*sizeof(cl_int), NULL, &err);
  clerror(err,"Couldn't create a buffer object");

  //printf("calling clSetKernelArg\n");
  /* Create kernel arguments from the CL buffers */
  err = clSetKernelArg(kernel, 0, sizeof(cl_mem), &piece_buff);
  if (err < 0) {
    perror("Couldn't set the kernel argument");
    exit(1);
  }

  //printf("limit = %d\n", limit);

  err = clSetKernelArg(kernel, 1, sizeof(cl_int), &depth);
  if (err < 0) {
    perror("Couldn't set the kernel argument");
    exit(1);
  }
  err = clSetKernelArg(kernel, 2, sizeof(cl_int), &piececount);
  if (err < 0) {
    perror("Couldn't set the kernel argument");
    exit(1);
  }
  err = clSetKernelArg(kernel, 3, sizeof(cl_int), &limit);
  if (err < 0) {
    perror("Couldn't set the kernel argument");
    exit(1);
  }
  // printf("local memory size = %d\n", max_workgroup_size*piececount*sizeof(cl_short)*2);
  err = clSetKernelArg(kernel, 4, max_workgroup_size*piececount*sizeof(cl_short), NULL);
  clerror(err,"Couldn't set the kernel argument");

  err = clSetKernelArg(kernel, 5, sizeof(cl_mem), &res_buff);
  clerror(err,"Couldn't set the kernel argument");


  //printf("calling clEnqueueWriteBuffer\n");
  err = clEnqueueWriteBuffer(queue, piece_buff, CL_TRUE, 0,
			     clplaced_size, clplaced, 0, NULL, NULL); 
  if (err < 0) {
    perror("error with clEnqueueWriteBuffer");
    exit(1);
  }

  /* Enqueue the kernel to the device */
  //printf("calling clEnqueueNDRangeKernel\n");
  err = clEnqueueNDRangeKernel(queue, kernel, 1, NULL, &total_work_units,
			       &max_workgroup_size, 0, NULL, &kernel_event);
  if (err < 0) {
    clerror(err, "Couldn't enqueue the kernel execution command");
    exit(1);
  }

  err = clWaitForEvents(1, &kernel_event);
  if(err < 0) {
    perror("Couldn't enqueue the kernel");
    exit(1);   
  }

  /* Read the result */

  clEnqueueReadBuffer(queue, res_buff, CL_TRUE, 0,
		      sizeof(cl_int)*total_work_units, result, 0, NULL, NULL);
  clerror(err, "Couldn't enqueue the read buffer command");
  
  //printf("calling clEnqueueReadBuffer\n");
  err = clEnqueueReadBuffer(queue, piece_buff, CL_TRUE, 0, clplaced_size,
			    clplaced, 0, NULL, NULL);
  clerror(err, "Couldn't enqueue the read buffer command");

  for(i=0;i<total_work_units;i++) {
    nodes += result[i];
  }

  //printf("kernel call complete\n");

  /* Deallocate resources */
  clReleaseMemObject(piece_buff);
  clReleaseMemObject(res_buff);
  free(result);
  return nodes;
}

// run_clsearch()
//
// This function calls clsearch() to find a solution for one of the
// positions in the clsearch array. It then looks at the state of each
// of the positions to determine whether the search needs to be
// repeated or to return. We would return if one of the searches
// completed and there are more positions to search or if all of the
// searches have completed.

long
run_clsearch(int depth, int limit, int mindepth, int toend) {
  static int count=0, active_count=0;
  int done=0,i,j,res_depth, res;
  static long total_nodes=0;
  time_t total_time;

  //printf("run_clsearch(depth=%d,limit=%d,mindepth=%d,toend=%d)\n", depth, limit, mindepth, toend);
  //printf("ready to search\n");
  while(!done) {
    if(!(count%10) && !quiet) {
      total_time = time(NULL)-start_time;
      printf("search #%d,active=%d,nodes=%ld,time=%zu,mnps=%.3f\n", count, active_count, total_nodes,total_time,
	     total_nodes/(1000000.0*total_time));
    }
    active_count=0;
    res = clsearch(mindepth, limit);
    //printf("searched %d nodes\n", res);
    total_nodes += res;

    if(toend) {
      done=1;
    }
    for(i=0;i<total_work_units;i++) {
      res_depth=-1;
      for(j=0;j<piececount;j++) {
	if(clplaced[i*piececount+j] > 0) {
	  res_depth=j;
	} else {
	  break;
	}
      }
      res_depth++;
      //printf("search #%d/%d depth %d\n", count, i, res_depth);
      if(res_depth == piececount) {
	active_count++;
	// search with match
	printf("%d %03d ", count, i);
	print_solution_martin(clplaced+piececount*i, res_depth, ++clsolcount);
	if(toend) {
	  done=0;
	}
      } else if(res_depth <= mindepth) {
	// complete search no match
	//printf("%d no solution found #%d\n", count, i);
	if(!toend) {
	  done=1;
	}
      } else {
	active_count++;
	// incomplete search
	if(toend) {
	  done=0;
	}
      }
    }
    count++;
  }
  if(toend) {
    printf("search #%d,nodes=%ld,time=%zu,mnps=%.3f\n", count, total_nodes,total_time,
	   total_nodes/(1000000.0*total_time));
    printf("solution count = %ld\n", clsolcount);
  }
  return total_nodes;
}

int search_count = 0;

// add_clsearch()
//
// This function takes a position (pointed to by placed pointer) and
// assigns it to a work item by putting it in the clplaced array. If
// this fills up the clplaced array then the function calls
// run_clsearch to start searching.

void
add_clsearch(short *placed, int depth, int limit, int mindepth) {
  int i,j,k,res_depth,done=0;
  //printf("add_clsearch(x,%d,%d,%d)\n", depth, limit, mindepth);

  search_count++;

  for(i=0;i<total_work_units;i++) {
    res_depth=-1;
    for(j=0;j<piececount;j++) {
      if(clplaced[i*piececount+j] > 0) {
	res_depth=j;
      } else {
	break;
      }
    }
    res_depth++;
    if(res_depth <= mindepth) {
      if(!done) {
	//printf("storing %d in clplaced #%d %d: ", search_count-1, i, depth);
	//print_solution_martin(placed, depth-2, 1);
	for(k=0;k<piececount;k++) {
	  //printf("(%d) ", placed[k]);
	  clplaced[i*piececount+k] = placed[k];
	}
	//	printf("\n");
	placed[depth-1] = 0;
	done=1;
      } else {
	//printf("clplaced #%d is empty\n", i);
	return; // clplaced isn't full
      }
    }
  }
  run_clsearch(depth, limit, mindepth, 0);
}

void
print_usage() {
  printf("usage: Eternity [options] puzzle_name { num_pieces solution_number }\n");
  printf("options:\n");
  printf("  -cl        use OpenCL\n");
  printf("  -limit x   max number of nodes searched per work item\n");
  printf("  -maxwgs x  max workgroup size\n");
  printf("  -maxcu x   max compute units\n");
  printf("  -q         quiet\n");
  printf("  -cpu       use OpenCL CPU device instead of GPU\n");
  exit(0);
}

int
main(int argc, char *argv[]) {
  int i, target, min, max, phase, cl=0, depth, limit=1000, doprint;
  long res,total=0;
  short *placed;

  setbuf(stdout,0);

  printf("args: ");
  for(i=0;i<argc;i++) {
    printf("%s ", argv[i]);
  }
  printf("\n");

  argc--; argv++;

  if (argc < 1) {
    print_usage();
  }

  while (argv[0][0] == '-') {
    if (!strcmp(argv[0], "-cl")) {
      argc--; argv++;
      cl=1;
    } else if (!strcmp(argv[0], "-limit")) {
      argc--; argv++;
      limit=atoi(argv[0]);
      argc--; argv++;
    } else if (!strcmp(argv[0], "-maxwgs")) {
      argc--; argv++;
      maxwgs=atoi(argv[0]);
      argc--; argv++;
    } else if (!strcmp(argv[0], "-maxcu")) {
      argc--; argv++;
      maxcu=atoi(argv[0]);
      argc--; argv++;
    } else if (!strcmp(argv[0], "-q")) {
      argc--; argv++;
      quiet=1;
    } else if (!strcmp(argv[0], "-cpu")) {
      argc--; argv++;
      usecpu=1;
    } else {
      printf("unknown option %s\n", argv[0]);
      print_usage();
    }
  }

  for (i=0;pi[i].width;i++) {
    if (!strcmp(pi[i].name,argv[0])) {
      break;
    }
  }
  if (!pi[i].width) {
    printf("puzzle %s not found\n",argv[0]);
    exit(1);
  }
  pieces = pi[i].pieces;
  width = pi[i].width;
  height = pi[i].height;

  init();

  if (cl) {
    clinit();
  }

  start_time = time(NULL);

  placed = malloc(width*height*sizeof(cl_short));
  for (i=0;i<width*height;i++) {
    placed[i] = (i==0) ? 2 : 0;
  }

  argc--; argv++;

  if (cl && argc%2 == 0) {
    printf("selected opencl search with incorrect number of arguments\n");
    exit(1);
  }

  min=0;
  phase=1;
  while (argc >= 0) {
    total=solcount=0;
    do {
      if (argc > 0) {
	max = atoi(argv[0]);
      } else {
	max = piececount;
      }
      if (argc > 1) {
	target = atoi(argv[1]);
      } else {
	if(cl) {
	  target = -2;
	} else {
	  target = -1;
	}
      }
      if(argc<2) {
	doprint=1;
	if(!cl) {
	  doprint=2;
	}
      } else {
	doprint=0;
      }

      //printf("%d: calling mysearch(placed,%d,%d,%d,%d,%d): \n", phase, min, max, doprint, target, limit);
      res = mysearch(placed, min, max, doprint, target, 10000000);
      //printf("result = %ld, total = %ld, count = %ld\n", res, total, solcount);
      total += res;
      for (depth=0;depth<piececount;depth++) {
	if (placed[depth] <= 0) {
	  break;
	}
      }
      //printf("depth = %d\n", depth);
      if (target == -2 && res == 0 && depth > 0) {
	res = -2;
      }
      if (res && depth >= max && argc < 2) {
	if (cl) {
	  add_clsearch(placed, depth, limit, max);
	} else {
	  print_solution_martin(placed, depth, solcount);
	}
      } else {
	if(res == -2) {
	  res = 0;
	}
	printf("result = %ld, total = %ld, count = %ld\n", res, total, solcount);
      }
    } while (res);

    min=max;
    argc -= 2;
    argv += 2;
    phase++;
  }

  if(cl) {
    total += run_clsearch(depth, limit, max, 1);
    printf("searched %ld nodes\n", total);
  }

  printf("total = %ld|count = %ld|time=%zu|best=%d\n", total, solcount, time(NULL)-start_time, best);
  printf("search complete\n");

  if (cl) {
    clReleaseKernel(kernel);
    clReleaseCommandQueue(queue);
    clReleaseProgram(program);
    clReleaseContext(context);
  }

  exit(0);
}
