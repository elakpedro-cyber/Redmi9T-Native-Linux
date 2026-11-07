/* Offline QEMU initramfs helper: rescue BusyBox has no module applets. */
#define _GNU_SOURCE
#include <fcntl.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>
int main(int argc,char **argv)
{
 if(argc!=2)return 2;
 if(!strcmp(argv[1],"load")) {
  int fd=open("/test-only.ko",O_RDONLY);if(fd<0)return 1;
  int result=syscall(SYS_finit_module,fd,"",0);close(fd);
  if(result<0){perror("finit_module");return 1;}return 0;
 }
 if(!strcmp(argv[1],"unload")) {
  if(syscall(SYS_delete_module,"lemon_touch_test",O_NONBLOCK)<0){
   if(errno==ENOSYS){puts("V8B_MODULE_UNLOAD_UNAVAILABLE; VM teardown required");return 0;}
   perror("delete_module");return 1;}return 0;
 }
 return 2;
}
