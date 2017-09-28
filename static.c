  for(pos=0; pos<width*height; pos++) {
    j=fit_table2[cursors[pos]];
    if(j >= 0) {
      placed[j/4]--;
    }
    
    j = fit_table2[++cursors[pos]];
    if(j < 0) {
      if(pos==0) {
	printf("no solution\n");
	break;
      }
      // no more pieces to try in this position
      pos -= 2;
      continue;
    }
    placed[j/4]++;
    if(placed[j/4]>1) {
      // the piece we are trying was already placed
      pos--;
      continue;
    }

    if(!(++nodes % 10000000)) {
      speed_report(nodes,0);
    }

    if(pos>=best) {
      print_puz(pos);
      best = pos+1;
    }

    row=(pos+1)/width;
    col=(pos+1)%width;
    down = (row == height-1);
    right = (col == width-1);
    if(col==0) {
      left=0;
    } else {
      k=fit_table2[cursors[pos]];
      left=pieces[k/4][(5-k%4)%4];
    }
    if(row==0) {
      up=0;
    } else {
      k=fit_table2[cursors[pos-width+1]];
      up=pieces[k/4][(6-k%4)%4];
    }
    // figure out what fits in the next spot
    cursors[pos+1] = fit_table1[(left*edgecount+up)*4+down*2+right]-1;
  }
  
  print_puz(pos);
