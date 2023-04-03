// emcc -s EXPORTED_FUNCTIONS="['_main','_origmain']" -O2 -o b.js b10x10.c

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif

#include <time.h>

#include "genheader1.c"
long long nodes=0, nodes2=0, nodes3=0, target1, target2, save_nodes;
int cursors[WIDTH*HEIGHT], best=0, core, restoring=0, solutions=0;
int specialp[WIDTH*HEIGHT], special=0;

time_t start_time;

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

  printf("best %d: ", pos);
  for(i=0; i<=pos; i++) {
    printf("%d/%d ", fit_table2[cursors[i]]/4+1, fit_table2[cursors[i]]%4);
  }
  printf("\n");
  fflush(stdout);

  if (pos+1 == HEIGHT*WIDTH) {
    printf("solved\n");
    solutions += 1;
  }

#ifdef __EMSCRIPTEN__
  sprintf(buf, "postMessage({msgType:'best',data:[");
  for(i=0; i<=pos; i++) {
    sprintf(buf+strlen(buf), "[%d,%d],", fit_table2[cursors[i]]/4+1, fit_table2[cursors[i]]%4);
  }
  strcpy(buf+strlen(buf),"]})");
  emscripten_run_script(buf);
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
  fprintf(fp, "./b10x10.exe %d %lld %lld %lld %ld %d\n", core, target1, nodes3, 
	  nodes, time(NULL)-start_time, best);
  fclose(fp);
  rename(filename, filename2);
  return 0;
}

long long last_report=0;

void
speed_report(long long nodes, int last, int curr) {
  static int status_num=0;
  char msg[256];
  char msg2[256];
  if (last == 0 && nodes - last_report < 400000000) {
    return;
  }
  last_report = nodes;
  if(last) {
    printf("%d solutions\n", solutions);
    printf("total ");
  } else {
    printf("status #%d,active=1,", status_num++);
  }
  sprintf(msg,"nodes=%lld,time=%ld,best=%d,nmps=%.3f,depth=%d",
	  nodes,
	  time(NULL)-start_time,
	  best,
	  nodes/(1000000.0*(time(NULL)-start_time)),
	  curr);
  puts(msg);
  fflush(stdout);
#ifdef __EMSCRIPTEN__
  sprintf(msg2, "postMessage({msgType:'status',data:'%s','core':%d});", msg, core);
  emscripten_run_script(msg2);
#endif
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
    for(j=0;j<sizeof(fit_table2)/4; j++) {
      if(fit_table2[j] != -1) {
	for(m=j;m<sizeof(fit_table2)/4;m++) {
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

    //init
    for(pos=0; pos<width*height; pos++) {
      placed[pos]=0;
    }
    //placed[0] = 1;
    cursors[0] = 2;
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
origmain(char *argv1, char *argv2) {
//origmain(int argc, char *argv[]) {}
  char msg[128];
  unsigned int rnd=0;
  nodes=nodes2=nodes3=0;
  best=0;
  core = atoi(argv1);
  FILE *fp = fopen("/dev/urandom", "r");
  rnd = rnd*256+(unsigned char) getc(fp);
  rnd = rnd*256+(unsigned char) getc(fp);
  rnd = rnd*256+(unsigned char) getc(fp);
  rnd = rnd*256+(unsigned char) getc(fp);
  fclose(fp);
  printf("seed = %u\n", rnd);

  srand(time(NULL)*1000+getpid()%1000);
  //srand(rnd);
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

  start_time=time(NULL);

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
  /* while(1) { */
  /*   repeat_search(); */
  /*   //printf("restarting search\n"); */
  /* } */
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
  emscripten_run_script("onmessage = function(e) { console.log('Message received from main script: ' + e.data);Module.ccall('origmain','number',['string','string'],['0',e.data]);}");
  emscripten_run_script("postMessage('message from worker');");
  printf("and we're off...\n");
}

#else

int
main(int argc, char *argv[]) {
  origmain(argv[1],argv[2]);
  exit(0);
}

#endif
