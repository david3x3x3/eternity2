// emcc -s EXPORTED_FUNCTIONS="['_main','_origmain']" -O2 -o b.js b10x10.c

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif

#include <time.h>

extern void init_ssearch();
extern int ssearch(int);

#include "genheader1.c"
long long nodes=0, nodes2=0, nodes3=0, target1, target2, save_nodes;
int cursors[WIDTH*HEIGHT], best=0, bestskips=0, restoring=0, solutions=0;
int specialp[WIDTH*HEIGHT], specials[WIDTH*HEIGHT], special=0;
int hintcount=0;
unsigned int core;

time_t start_time, last_report_time;

#ifdef __EMSCRIPTEN__
char best_buf[8192];
#endif
int best_buf_printed=1;

void
print_puz(int pos) {
  int i, r, c;
  char buf[8192];
  
  // printf("best solution %d: ", pos+1);
  /* for(r=0; r<HEIGHT; r++) { */
  /*   for(c=0; c<WIDTH; c++) { */
  /*     if (r*width+c <= pos) { */
  /* 	printf("%02x ", fit_table2[cursors[r*WIDTH+c]]/4); */
  /*     } else { */
  /* 	printf(".. "); */
  /*     } */
  /*   } */
  /*   printf("\n"); */
  /* } */
#if 0
  for(i=0; i<=pos; i++) {
    printf("%d ", cursors[i]);
  }
  printf("\n");

  for(i=0; i<=pos; i++) {
    printf("%d ", fit_table2[cursors[i]]);
  }
  printf("\n");
  
  for(i=1330; i<1340; i++) {
    printf("%d ", fit_table2[i]);
  }
  printf("\n");
#endif

#ifndef __EMSCRIPTEN__
  printf("best %d: ", pos);
  for(i=0; i<=pos; i++) {
    printf("%d/%d ", fit_table2[cursors[i]]/4+1, fit_table2[cursors[i]]%4);
  }
  printf("\n");
  fflush(stdout);
#endif

  if (pos+1 == HEIGHT*WIDTH) {
    printf("solved\n");
    solutions += 1;
  }

#ifdef __EMSCRIPTEN__
  sprintf(best_buf, "postMessage({msgType:'best',data:[%d,[",pos);
  for(i=0; i<=pos; i++) {
    sprintf(best_buf+strlen(best_buf), "[%d,%d],", fit_table2[cursors[i]]/4+1, fit_table2[cursors[i]]%4);
  }
  strcpy(best_buf+strlen(best_buf),"]]})");
  best_buf_printed=0;
  //emscripten_run_script(best_buf);
#endif
}

int
save_restore() {
  FILE *fp;
  char filename[32];
  char filename2[32];

  if(restoring) {
    if(nodes3<target2) {
      printf("restore #%lld\n", nodes3);
      print_puz(20);
      return 1;
    } else {
      printf("done restoring; best = %d\n", best);
      restoring=0;
      nodes=save_nodes;
      return 0;
    }
  }
  printf("saving\n");
  sprintf(filename, "save%d.dat.tmp", core);
  sprintf(filename2, "save%d.dat", core);
  fp = fopen(filename, "w");
  fprintf(fp, "./b10x10.exe %d %lld %lld %lld %lld %d\n", core, target1, nodes3, 
	  nodes, time(NULL)-start_time, best);
  fclose(fp);
  rename(filename, filename2);
  return 0;
}

long long last_report=0;

void
speed_report(long long nodes, int last, int curr) {
  static int status_num=0;
  static long long interval=100000;
  char msg[256];
  char msg2[256];
  if (last == 0 && nodes - last_report < interval) {
    return;
  }
  last_report = nodes;
  if(last) {
    printf("%d solutions\n", solutions);
    printf("total ");
  } else {
    printf("status phase=1,");
  }
  sprintf(msg,"nodes=%lld,time=%lld,best=%d,skips=%04d,rate=%.3fm,depth=%d",
	  nodes,
	  time(NULL)-start_time,
	  best, bestskips,
	  nodes/(1000000.0*(time(NULL)-start_time)),
	  curr);
#ifdef __EMSCRIPTEN__
  if(!best_buf_printed) {
    emscripten_run_script(best_buf);
    best_buf_printed=1;
  }
  sprintf(msg2, "postMessage({msgType:'status',data:'phase=1,%s','core':%d});", msg, core);
  emscripten_run_script(msg2);
#else
  puts(msg);
  fflush(stdout);
#endif
  if (time(NULL)-last_report_time < 2) {
    interval *= 2;
  }
  last_report_time = time(NULL);
}

int placed[WIDTH*HEIGHT], downs[WIDTH*HEIGHT];

#include "genheader2.c"

void shuffle(int *array, size_t n)
{
    if (n > 1) 
    {
        size_t i;
        for (i = 0; i < n - 1; i++) 
        {
          size_t j = i + rand() / (RAND_MAX / (n - i) + 1);
          int t = array[j];
          array[j] = array[i];
          array[i] = t;
        }
    }
}

long long
mysearch(int func) {
  int j, k, m;
  static int pos, row, col, up, left, down, right;

  if (func == 0) {
    // shuffle
    for(j=0;fit_table2[j] != -2; j++) {
      if(fit_table2[j] != -1) {
	for(m=j;;m++) {
	  if(fit_table2[m] == -1) {
	    break;
	  }
	}
	shuffle(fit_table2 + j, m-j);
	j = m;
      }
    }
    // count special edges
    m = 0;
    for (j=0;j<width*height;j++) {
      specialp[j] = 0;
    }
    for (j=0;j<width*height;j++) {
      for (k=0;k<4;k++) {
	if (pieces[j][k] == 6 || pieces[j][k] == 7) {
	  specialp[j] += 1;
	  m += 1;
	}
      }
    }
    for (j=0;j<width*height;j++) {
      if      (j==8)   { specials[j] =  5; } else if (j==16)  { specials[j] =  9; }
      else if (j==32)  { specials[j] = 24; } else if (j==40)  { specials[j] = 33; }
      else if (j==48)  { specials[j] = 42; } else if (j==56)  { specials[j] = 51; }
      else if (j==64)  { specials[j] = 60; } else if (j==72)  { specials[j] = 68; }
      else if (j==82)  { specials[j] = 76; } else if (j==90)  { specials[j] = 81; }
      else if (j==102) { specials[j] = 85; } else if (j==110) { specials[j] = 89; }
      else if (j==118) { specials[j] = 92; } else if (j==132) { specials[j] = 95; }
      else if (j==148) { specials[j] = 97; } else if (j==160) { specials[j] = 98; }
      else { specials[j] = 0; }
    }
      

    //init
    for(pos=0; pos<width*height; pos++) {
      placed[pos]=0;
    }
    int hintpcnum[] = { 138, 207, 254, 180, 248 };
    for(pos=0; pos<hintcount; pos++) {
      placed[hintpcnum[pos]] = 1;
    }
    
    //placed[0] = 1;
    cursors[0] = 2;
    init_ssearch();
  } else if(func == 1) {
    //run
#include "gensearch.c"
    printf("all done\n");
#ifdef __EMSCRIPTEN__
    //emscripten_cancel_main_loop();
#endif
  } else if(func == 2) {
    //resume
    //goto POS83;
  } else {
    return -1;
  }
  
  return 0;
}

void
repeat_search() {
  static int init=1;

  if(init) {
    mysearch(0); //init
    mysearch(1); //run
    init=0;
    return;
  }
  mysearch(2); //resume
}

int
origmain(char *argv1, char *argv2, char *argv3) {
//origmain(int argc, char *argv[]) {}
  char msg[128];
  unsigned int rnd=0;
  nodes=nodes2=nodes3=0;
  best=0;

  core = atoi(argv1);
  sprintf(msg,"postMessage('core = %d');", core);
#ifdef __EMSCRIPTEN__
  emscripten_run_script(msg);
#else
  puts(msg);
#endif

  target1 = atoll(argv2);
  sprintf(msg,"postMessage('target1 = %lld');", target1);
#ifdef __EMSCRIPTEN__
  emscripten_run_script(msg);
#else
  puts(msg);
#endif

  hintcount = atoi(argv3);
  sprintf(msg,"postMessage('hintcount = %d');", hintcount);
#ifdef __EMSCRIPTEN__
  emscripten_run_script(msg);
#else
  puts(msg);
#endif

#ifdef __EMSCRIPTEN__
  rnd = EM_ASM_INT({
      return Math.floor(Math.random() * 2**32);
    });
  sprintf(msg,"postMessage('seed = %u');", rnd);
  emscripten_run_script(msg);
  srand(rnd);
#else
  //srand(time(NULL)*1000+getpid()%1000);
  srand(core);
#endif

  start_time=time(NULL);
  last_report_time = start_time;

  /* if(argc > 3) { */
  /*   restoring=1; */
  /*   target2 = atoll(argv[3]); */
  /*   printf("target2 = %lld\n", target2); */
  /*   save_nodes = atoll(argv[4]); */
  /*   printf("save_nodes = %lld\n", save_nodes); */
  /*   start_time = atoi(argv[5]); */
  /*   printf("start_time = %ld\n", start_time); */
  /*   start_time = time(NULL)-start_time; */
  /*   best = atoi(argv[6]); */
  /*   printf("best = %d\n", best); */
  /* } */
  
  //setbuf(stdout,0);
  //#ifdef __EMSCRIPTEN__
#if 0
  emscripten_set_main_loop(repeat_search,0,0);
  emscripten_set_main_loop_timing(EM_TIMING_SETTIMEOUT, 0);
#else
  mysearch(0);
  mysearch(1);
#endif

#ifdef __EMSCRIPTEN__
  sprintf(msg, "postMessage({'msgType':'exit','nodes':'%lld','best':%d,'core':%d});", nodes, best, core);
  emscripten_run_script(msg);
#endif
  return 0;
}

#ifdef __EMSCRIPTEN__

int
main() {
  //  emscripten_run_script("onmessage = function(e) { console.log('Message received from main script: ' + e.data); Module.ccall('origmain','number',['string','string','string'],['whatever','0',e.data]); }");
  emscripten_run_script("onmessage = function(e) { console.log('Message received from main script: ' + e.data);Module.ccall('origmain','number',['string','string','string'],['0','0',e.data]);}");
  emscripten_run_script("postMessage('worker is ready');");
  printf("and we're off...\n");
}

#else

int
main(int argc, char *argv[]) {
  origmain(argv[1],argv[2], argv[3]);
  exit(0);
}

#endif
