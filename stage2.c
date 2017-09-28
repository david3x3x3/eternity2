#include <sys/types.h>
#include <unistd.h>
#include <time.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
  const char *name;
  int width;
  int height;
  int (*pieces)[4];
} puzinfo;

puzinfo *p;

time_t start_time;

#include "pieces.h"

// piece order is clockwise
// rotation 0 order is URDL

int *board, *placed, width, height, size, best;
long long nodes;

void
printboard() {
  int row, col, *ptr, num, rot, i;
  /* for(i=0;i<width*height*2;i++) { */
  /*   printf("%d ", board[i]); */
  /* } */
  /* printf("\n"); */
  for(row=0;row<height;row++) {
    for(col=0;col<width;col++) {
      ptr = &board[row*width*2+col*2];
      num = ptr[0];
      rot = ptr[1];
      if(num>=0) {
	printf("%d/%d ", num+1, rot);
      }
    }
    //printf("\n");
  }
  printf("\n");
}

int *rand_order,min_depth=999,max_depth=0;

long long int last_203 = 0;

int
search(int depth, int bad, int maxbad) {
  int row, col, *ptr, num, numr, rot, i, ok;
  int left, up, down, right, n_l_r, n_u_d, at_right, at_bottom;
  int row2, col2, num2, rot2, thisbad, at_edge;
  /* printf("search(%d,%d,%d)\n", depth, bad, maxbad); */

  /* if(bad > maxbad) { */
  /*   /\* printf("too many bad pieces\n"); *\/ */
  /*   return 0; */
  /* } */

  if(depth < 203) {
    maxbad = 0;
  } else if(depth < 218) {
    maxbad = 3;
  } else if(depth < 230) {
    maxbad = 8;
  } else if(depth < 241) {
    maxbad = 14;
  } else {
    maxbad = 19;
  }

  nodes++;

  if(depth < min_depth) min_depth = depth;
  if(depth > max_depth) max_depth = depth;

  if(!(nodes % 1000000)) {
    printf("status nodes = %lld M, time = %d, rate = %f, range=%d-%d %d\n", nodes/1000000, time(NULL)-start_time, ((nodes*1.0)/(time(NULL)-start_time))/1000000, min_depth, max_depth, (nodes-last_203)/1000000);
    min_depth=999;
    max_depth=0;
  }
  
  if(depth < 203 && 
     depth > 32 &&
     nodes - last_203 > 100000000) {
    if(depth==33) {
      printf("reset_best\n");
      last_203=nodes;
    }
    return 0;
  }

  if(depth >= 203) last_203 = nodes;

  if(depth >= best) {
    best = depth;
    printf("best solution %d-%d: ", depth, bad);
    printboard();
  }
  if(depth == width*height) {
    printf("found solution:\n");
    printboard();
    return 1;
  }
  row = depth/width;
  col = depth%width;
  at_right = (col + 1 == width);
  at_bottom = (row + 1 == height);
  //find edge above
  if(row) {
    row2 = row-1;
    col2 = col;
    num2 = board[row2*width*2+col2*2+0];
    rot2 = board[row2*width*2+col2*2+1];
    n_u_d = p->pieces[num2][(2+4-rot2)%4];
  } else {
    n_u_d = 0;
  }
  //find edge to left
  if(col) {
    row2 = row;
    col2 = col-1;
    num2 = board[row2*width*2+col2*2+0];
    rot2 = board[row2*width*2+col2*2+1];
    n_l_r = p->pieces[num2][(1+4-rot2)%4];
  } else {
    n_l_r = 0;
  }

  at_edge = (row==0 || row+1 == height || col==0 || col+1 == width);

  /* printf("at_right = %d\nat_bottom = %d\n", at_right, at_bottom); */
  for(numr=0;numr<height*width;numr++) {
    num = rand_order[numr];
    /* printf("trying piece %d\n", num); */
    if(placed[num]) {
      /* printf("already placed\n"); */
      continue;
    }

    /* check to see if this is an edge piece */
    if(at_edge != (p->pieces[num][0] == 0)) {
      /* printf("col = %d, piece = %d, first edge = %d, skipping\n", col, num, p->pieces[num][0]); */
      continue;
    }

    for(rot=0;rot<4;rot++) {
      /* printf("trying orientation %d\n", rot); */
      thisbad=0;
      up    = p->pieces[num][(0+4-rot)%4];
      right = p->pieces[num][(1+4-rot)%4];
      down  = p->pieces[num][(2+4-rot)%4];
      left  = p->pieces[num][(3+4-rot)%4];
      if(((row == 0) != (up == 0)) ||
	 ((col == 0) != (left == 0)) ||
	 (at_right != (right == 0)) ||
	 (at_bottom != (down == 0))) {
	/* printf("bad edge status\n"); */
	continue;
      }

      /* if((row == 0) != (up == 0)) {printf("bad edge status up\n"); continue;} */
      /* if((col == 0) != (left == 0)) {printf("bad edge status left\n"); continue;} */
      /* if((at_right != (right == 0))) {printf("bad edge status right\n"); continue;} */
      /* if(at_bottom != (down == 0)) {printf("bad edge status down\n"); continue;} */

      if(left != n_l_r) {
	thisbad++;
      }
      if(up != n_u_d) {
	thisbad++;
      }
      if(bad+thisbad > maxbad) {
	continue;
      }
      /* printf("placing %d/%d\n", num, rot); */
      board[row*width*2+col*2+0] = num;
      board[row*width*2+col*2+1] = rot;
      placed[num]=1;
      if(search(depth+1,bad+thisbad,maxbad)) {
	return 1;
      }
      /* printf("removing %d/%d\n", num, rot); */
      board[row*width*2+col*2+0] = -1;
      board[row*width*2+col*2+1] = -1;
      placed[num]=0;
    }
  }
  return 0;
}

int
main(int argc, char *argv[]) {
  char puzname[64], buf[64], *s;
  int piececount, i,j,k, row, col, maxbad;
  
  start_time = time(NULL);
  setbuf(stdout, 0);
  argv++; argc--;
  strcpy(puzname, argv[0]);
  argv++; argc--;
  printf("puzname = %s\n", puzname);
  printf("argc = %d\n", argc);
  piececount = argc;
  for(i=0;pi[i].name;i++) {
    if(!strcmp(puzname,pi[i].name))
      break;
  }
  if(!pi[i].name) {
    printf("puzzle %s not found\n", puzname);
    exit(1);
  }
  p = &pi[i];
  width = p->width;
  height = p->height;
  size = width*height;
  printf("width = %d\nheight = %d\n", p->width, p->height);
  board = malloc(height*width*2*sizeof(int));
  for(i=0;i<width*height*2;i++) {
    board[i] = -1;
  }
  placed = calloc(height*width,sizeof(int));

  // randomize the search_order
  srandom(time(NULL)*1000+getpid()%1000);
  rand_order = calloc(height*width,sizeof(int));
  for(i=0;i<size;i++) {
    rand_order[i] = i;
  }
  for(i=0;i<size;i++) {
    j = i+random()%(size-i);
    k = rand_order[j];
    rand_order[j] = rand_order[i];
    rand_order[i] = k;
  }
  printf("rand_order = ");
  for(i=0;i<size;i++) {
    printf("%d ", rand_order[i]);
  }
  printf("\n");

  for(i=0;i<piececount;i++) {
    strcpy(buf,argv[0]);
    argv++; argc--;
    printf("piece %d = %s\n", i, buf);
    s = strstr(buf, "/");
    *s++ = '\0';
    j = atoi(buf);
    k = atoi(s);
    //printf("%3d/%d ", j, k);
    row = i/width;
    col = i%width;
    board[row*width*2+col*2] = j-1;
    board[row*width*2+col*2+1] = k;
    placed[j-1] = 1;
    if(!((i+1)%width)) {
      printf("\n");
    }
  }
  printf("\n");
  printboard();
  for(maxbad=0;;maxbad++) {
    if(maxbad==1) {
      continue; // there will never be one mismatch
    }
    best=0;
    nodes=0;
    if(search(piececount, 0, maxbad)) {
      printf("\nfound solution with score %d\n",(width-1)*height+width*(height-1)-maxbad);
      break;
    }
    printf("\nno solution with maxbad = %d (best = %d, nodes = %lld)\n", maxbad, best, nodes);
  }
  exit(0);
}
