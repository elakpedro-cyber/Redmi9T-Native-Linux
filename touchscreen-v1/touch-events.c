/* SPDX-License-Identifier: MIT. Explicit Stage1 evdev recording, no grabs/injection. */
#define _POSIX_C_SOURCE 200809L
#include <fcntl.h>
#include <linux/input.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <time.h>
#include <unistd.h>
static double seconds(void)
{ struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9; }
int main(int argc,char **argv)
{
 if(argc!=4 || strcmp(argv[3],"--ack-input-open")) {
  fprintf(stderr,"usage: touch-events /dev/input/eventN SECONDS --ack-input-open\nOpening a device may enable its IRQ; separate hardware authorization is required.\n");return 2;
 }
 const char *path=argv[1], *prefix="/dev/input/event";
 if(strncmp(path,prefix,strlen(prefix))||!path[strlen(prefix)]||strspn(path+strlen(prefix),"0123456789")!=strlen(path+strlen(prefix)))return 2;
 char *end;long duration=strtol(argv[2],&end,10);if(*end||duration<1||duration>30)return 2;
 char sys[256], name[128]={0};
 snprintf(sys,sizeof(sys),"/sys/class/input/%s/device/name",path+strlen("/dev/input/"));
 FILE *file=fopen(sys,"r");if(!file)return 3;
 if(!fgets(name,sizeof(name),file)){fclose(file);return 3;}fclose(file);
 name[strcspn(name,"\n")]=0;
 if(strcmp(name,"Lemon NT36672A handoff touchscreen")){fprintf(stderr,"Unknown input identity; not opened\n");return 3;}
 int fd=open(path,O_RDONLY|O_NONBLOCK|O_CLOEXEC);if(fd<0){perror("open");return 3;}
 struct stat st;unsigned long properties=0,abs=0;
 if(fstat(fd,&st)||!S_ISCHR(st.st_mode)||major(st.st_rdev)!=13||ioctl(fd,EVIOCGNAME(sizeof(name)),name)<0||strcmp(name,"Lemon NT36672A handoff touchscreen"))goto fail;
 if(ioctl(fd,EVIOCGPROP(sizeof(properties)),&properties)<0||!(properties&(1UL<<INPUT_PROP_DIRECT)))goto fail;
 if(ioctl(fd,EVIOCGBIT(EV_ABS,sizeof(abs)),&abs)<0)goto fail;
 unsigned long required=(1UL<<ABS_MT_SLOT)|(1UL<<ABS_MT_TRACKING_ID)|(1UL<<ABS_MT_POSITION_X)|(1UL<<ABS_MT_POSITION_Y);
 if((abs&required)!=required)goto fail;
 struct input_absinfo x,y;
 if(ioctl(fd,EVIOCGABS(ABS_MT_POSITION_X),&x)||ioctl(fd,EVIOCGABS(ABS_MT_POSITION_Y),&y))goto fail;
 printf("{\"event\":\"metadata\",\"x_min\":%d,\"x_max\":%d,\"y_min\":%d,\"y_max\":%d}\n",x.minimum,x.maximum,y.minimum,y.maximum);
 double deadline=seconds()+duration;
 while(seconds()<deadline) {
  struct pollfd pollfd={.fd=fd,.events=POLLIN};int ms=(int)((deadline-seconds())*1000);if(ms<0)break;
  int ret=poll(&pollfd,1,ms);if(ret==0)break;if(ret<0||pollfd.revents&(POLLERR|POLLHUP))goto fail;
  struct input_event data[64];ssize_t n=read(fd,data,sizeof(data));if(n<=0||n%sizeof(data[0]))goto fail;
  for(size_t i=0;i<(size_t)n/sizeof(data[0]);i++) {
   if(data[i].type==EV_SYN&&data[i].code==SYN_DROPPED){fprintf(stderr,"SYN_DROPPED: stop and resynchronize before GUI use\n");goto fail;}
   if(data[i].type==EV_SYN||data[i].type==EV_ABS||(data[i].type==EV_KEY&&data[i].code==BTN_TOUCH))
    printf("{\"type\":%u,\"code\":%u,\"value\":%d}\n",data[i].type,data[i].code,data[i].value);
  }
  fflush(stdout);
 }
 close(fd);return 0;
fail: fprintf(stderr,"Input validation/read failure; recording stopped\n");close(fd);return 4;
}
