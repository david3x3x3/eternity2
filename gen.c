#include <stdio.h>

//#define WIDTH 10
//#define HEIGHT 10

extern int width, height;
extern int (*pieces)[4];
extern int edgecount;
extern char *fit_table_buffer;

void
gen(int target1, int target2, int target3) {
  int i, pos, row, col, up, left, down, right, prev_was_hint=0;
  
  /* target1=atoi(argv[1]); */
  /* target2=atoi(argv[2]); */

  //placed[0] = 1;
  //cursors[0] = 2;
  //best=0;

  setbuf(stdout,0);

  printf("#define WIDTH %d\n", width);
  printf("#define HEIGHT %d\n", height);
  printf("%s;\n", fit_table_buffer);
  printf("int pieces_left[][4]={");
  for(pos=0; pos<width*height; pos++) {
    printf("{");
    for(i=0;i<4;i++) {
      printf("%d,", pieces[pos][i]*edgecount*4);
    }
    printf("},");
  }
  printf("};\n");

  printf("int pieces_up[][4]={");
  for(pos=0; pos<width*height; pos++) {
    printf("{");
    for(i=0;i<4;i++) {
      printf("%d,", pieces[pos][i]*4);
    }
    printf("},");
  }
  printf("};\n");
  

  for(pos=0; pos<width*height; pos++) {
    printf("POS%d:\n", pos);
    printf("    j = fit_table2[++cursors[%d]];\n", pos);
    puts("    if(j < 0) {");
    if(pos==0) {
      puts("      printf(\"no more solutions\\n\");");
      printf("      speed_report(nodes,1,0);\n");
      printf("      goto POS%d;\n", width*height);
    } else {
      puts("      // no more pieces to try here");
      if(prev_was_hint) {
	printf("      if (hintcount < %d)\n", prev_was_hint);
      }
      printf("      placed[fit_table2[cursors[%d]]/4]=0;\n", pos-1);
      printf("      goto POS%d;\n", pos-1);
    }
    puts("    }");
    prev_was_hint = 0;
    int hint=0;
    int hintpos[] = { 135, 34, 45, 210, 221 };
    int hintpc[] = { 138*4+2, 207*4+3, 254*4+3, 180*4+3, 248*4+0 };
    int hintedge = -1;
    for(hint=0;hint<5;hint++) {
      if (pos == hintpos[hint]) {
	break;
      } else if(pos+16 == hintpos[hint]) {
	hintedge = pieces[hintpc[hint]/4][(4-hintpc[hint]%4)%4];
	break;
      }
    }
    if (hint != 5) {
      if (hintedge != -1) {
	printf("    if(placed[j/4] || (hintcount >= %d && pieces[j/4][(6-j%%4)%%4] != %d)) {\n", hint+1, hintedge);
      } else {
	printf("    if((hintcount < %d && placed[j/4]) || (hintcount >= %d && j != %d)) {\n", hint+1, hint+1, hintpc[hint]);
	prev_was_hint = hint+1;
      }
    } else {
      printf("    if(placed[j/4]) {\n");
    }
    puts("      // the piece we are trying was already placed");
    puts("      // or is incorrect because of hints");
    printf("      goto POS%d;\n", pos);
    puts("    }");
    if(pos+1 == target1) {
      printf("    if(nodes2++ != target1) {\n");
      printf("      goto POS%d;\n", pos);
      printf("    }\n");

    }
    puts("    placed[j/4]=1;");
    if(pos >= target1) {
      puts("    ++nodes;");
    }
    if(pos+1 == target2) {
      printf("    nodes3++;\n");
      printf("    if(save_restore()) goto POS%d;\n", pos);
    }
 
    printf("    downs[%d]=pieces_up[j/4][(6-j%%4)%%4];\n", pos);

    if(pos >= target3) {
      //puts("    if(!(nodes % 100000000)) {");
      printf("    speed_report(nodes,0,%d);\n", pos);
      //puts("    printf(\"%ld nodes\\n\", nodes);");
      //puts("    }");
      puts("");
      printf("    if(best<%d) {\n", pos+1);
      if(pos+1 < width*height) {
	printf("      print_puz(%d);\n", pos);
      }
      printf("      best = %d;\n", pos+1);
      puts("    }");
    }
    if(pos+1 < width*height) {
      row = (pos+1)/width;
      //printf("    row=%d;\n", row);
      col = (pos+1)%width;
      //printf("    col=%d;\n", col);
      down = (row == height-1);
      //printf("    down = %d;\n", down); //to do: only set when this changes
      right = (col == width-1);
      //printf("    right = %d;\n", right);
      if(col==0) {
	left=0;
	//puts("    left=0;");
      } else {
	left=999;
	//printf("    k=fit_table2[cursors[%d]];\n", pos);
	//puts("    left=pieces[k/4][(5-k%4)%4];");
	printf("    left=pieces_left[j/4][(5-j%%4)%%4];\n");
      }
      if(row==0) {
	up=0;
	//puts("    up=0;");
      } else {
	up=999;
	printf("    up=downs[%d];\n", pos-width+1);
      }
      puts("    // figure out what fits in the next spot");
      printf("    cursors[%d] = fit_table1[", pos+1);
      if(left) {
	printf("left");
      } else {
	printf("0");
      }
      if(up) {
	printf("+up");
      }
      printf("+%d]-1;\n", down*2+right);
    } else {
      printf("    //solved\n");
      printf("    print_puz(%d);\n", pos);
      printf("    placed[fit_table2[cursors[%d]]/4]=0;\n", pos);
      printf("    goto POS%d;\n", pos);
    }
  }
  printf("POS%d:\n", pos);
  //print_puz(pos);
}
