#include <assert.h>
#include <fcntl.h>
#include <linux/input.h>
#include <poll.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
int main(int argc,char **argv)
{
 assert(argc==2);
 int fd=open(argv[1],O_RDONLY|O_NONBLOCK);
 assert(fd>=0);
 char name[128]={0};assert(ioctl(fd,EVIOCGNAME(sizeof(name)),name)>=0);
 assert(!strcmp(name,"lemon-nvt-offline-test"));
 unsigned long props=0;
 assert(ioctl(fd,EVIOCGPROP(sizeof(props)),&props)>=0 && (props&(1UL<<INPUT_PROP_DIRECT)));
 struct input_absinfo info;
 assert(ioctl(fd,EVIOCGABS(ABS_MT_POSITION_X),&info)==0 && info.maximum==1079);
 assert(ioctl(fd,EVIOCGABS(ABS_MT_POSITION_Y),&info)==0 && info.maximum==2339);
 unsigned frames=0,downs=0,ups=0,positions=0;
 int slots[10];for(unsigned i=0;i<10;i++)slots[i]=-1;
 unsigned slot=0;
 while(frames<3) {
  struct pollfd p={.fd=fd,.events=POLLIN};assert(poll(&p,1,2000)==1);
  struct input_event ev[32];ssize_t n=read(fd,ev,sizeof(ev));assert(n>0 && n%sizeof(ev[0])==0);
  for(unsigned i=0;i<(unsigned)n/sizeof(ev[0]);i++) {
   if(ev[i].type==EV_ABS) {
    if(ev[i].code==ABS_MT_SLOT){slot=ev[i].value;assert(slot<10);}
    if(ev[i].code==ABS_MT_TRACKING_ID) {
     if(ev[i].value<0){assert(slots[slot]>=0);slots[slot]=-1;ups++;}
     else {assert(slots[slot]<0);for(unsigned j=0;j<10;j++)assert(slots[j]!=ev[i].value);slots[slot]=ev[i].value;downs++;}
    }
    if(ev[i].code==ABS_MT_POSITION_X||ev[i].code==ABS_MT_POSITION_Y)positions++;
   }
   if(ev[i].type==EV_SYN&&ev[i].code==SYN_REPORT)frames++;
   assert(!(ev[i].type==EV_SYN&&ev[i].code==SYN_DROPPED));
  }
 }
 assert(downs==2 && ups==2 && positions>=4);
 for(unsigned i=0;i<10;i++)assert(slots[i]==-1);
 close(fd);
 puts("REAL_ARM64_EVDEV_PASS TypeB slots tracking_ids two_contacts motion release 1080x2340");
 return 0;
}
