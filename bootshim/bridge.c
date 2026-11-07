#include <stdint.h>
#include <stddef.h>
#include <libfdt.h>

#define KERNEL_ADDR 0x80000000UL
#define DTB_ADDR 0x82000000UL
#define DTB_SPACE 0x20000UL
extern __attribute__((visibility("hidden"))) const unsigned char native_image[], native_image_end[];
extern __attribute__((visibility("hidden"))) const unsigned char native_dtb[], native_dtb_end[];
extern __attribute__((visibility("hidden"))) const unsigned char _start[], wrapper_end[];
extern void prepare_range_poc(uint64_t address,uint64_t size);
extern void clean_range_poc(uint64_t address,uint64_t size);

void *memcpy(void *d, const void *s, size_t n) {
    unsigned char *a=d; const unsigned char *b=s;
    while(n--) *a++=*b++;
    return d;
}
void *memmove(void *d, const void *s, size_t n) {
    unsigned char *a=d; const unsigned char *b=s;
    if(a<b) return memcpy(d,s,n);
    while(n) { n--; a[n]=b[n]; }
    return d;
}
void *memset(void *d, int c, size_t n) {
    unsigned char *a=d; while(n--) *a++=c; return d;
}
int memcmp(const void *a, const void *b, size_t n) {
    const unsigned char *x=a,*y=b;
    while(n--) { if(*x!=*y) return *x-*y; x++; y++; } return 0;
}
size_t strlen(const char *s) { size_t n=0; while(s[n]) n++; return n; }
size_t strnlen(const char *s,size_t n) { size_t i=0;while(i<n&&s[i])i++;return i; }
int strcmp(const char *a,const char *b) { while(*a&&*a==*b){a++;b++;}return (unsigned char)*a-(unsigned char)*b; }
int strncmp(const char *a,const char *b,size_t n) { while(n&&*a&&*a==*b){a++;b++;n--;}return n?(unsigned char)*a-(unsigned char)*b:0; }
void *memchr(const void *s,int c,size_t n) { const unsigned char *p=s;while(n--){if(*p==(unsigned char)c)return (void *)p;p++;}return NULL; }
char *strrchr(const char *s,int c) { const char *last=NULL;do{if(*s==(char)c)last=s;}while(*s++);return (char *)last; }

__attribute__((noreturn,noinline)) void halt(unsigned reason) {
    asm volatile("mov x0, %0" :: "r"((uint64_t)reason) : "x0");
    for(;;) asm volatile("wfe");
}
static int overlap(uint64_t a,uint64_t n,uint64_t b,uint64_t m) {
    if(a+n<a||b+m<b) halt(1);
    return a<b+m&&b<a+n;
}
static uint64_t be64(const fdt32_t *p) {
    return ((uint64_t)fdt32_to_cpu(p[0])<<32)|fdt32_to_cpu(p[1]);
}
static uint64_t address(const void *p,int len) {
    if(len==8) return be64(p);
    if(len==4) return fdt32_to_cpu(*(const fdt32_t *)p);
    halt(2);
}
static int memory_node(const void *dt) {
    int n=fdt_node_offset_by_prop_value(dt,-1,"device_type","memory",7);
    if(n<0||fdt_node_offset_by_prop_value(dt,n,"device_type","memory",7)>=0) halt(3);
    return n;
}
static void reserved(const void *dt,uint64_t a,uint64_t size) {
    int parent=fdt_path_offset(dt,"/reserved-memory"), n;
    if(parent>=0) {
        if(fdt_address_cells(dt,parent)!=2||fdt_size_cells(dt,parent)!=2) halt(4);
        fdt_for_each_subnode(n,dt,parent) {
            int len;const fdt32_t *r=fdt_getprop(dt,n,"reg",&len);
            if(!r) continue;
            if(len%16) halt(5);
            for(int i=0;i<len/4;i+=4)
                if(overlap(a,size,be64(r+i),be64(r+i+2))) halt(6);
        }
    }
    for(int i=0;i<fdt_num_mem_rsv(dt);i++) {
        uint64_t base,len;
        if(fdt_get_mem_rsv(dt,i,&base,&len)||overlap(a,size,base,len)) halt(7);
    }
}
static void destination(const void *incoming,const fdt32_t *ram,int len,uint64_t a,uint64_t size,uint64_t initrd,uint64_t rdlen) {
    int found=0;
    for(int i=0;i<len/4;i+=4) {
        uint64_t base=be64(ram+i), bytes=be64(ram+i+2);
        if(base+bytes<base) halt(8);
        if(a>=base&&a+size>=a&&a+size<=base+bytes)found=1;
    }
    if(!found)halt(9);
    if(overlap(a,size,initrd,rdlen)||overlap(a,size,(uintptr_t)_start,(uintptr_t)wrapper_end-(uintptr_t)_start)||overlap(a,size,(uintptr_t)incoming,fdt_totalsize(incoming)))halt(10);
    reserved(incoming,a,size);reserved(native_dtb,a,size);
}
static void source_range(const void *incoming,const fdt32_t *ram,int len,uint64_t initrd,uint64_t rdlen) {
    uint64_t base=(uintptr_t)_start,size=(uintptr_t)wrapper_end-base;
    int found=0;
    if(!size||base+size<base||(base&0xfff))halt(32);
    for(int i=0;i<len/4;i+=4) {
        uint64_t start=be64(ram+i),bytes=be64(ram+i+2);
        if(start+bytes<start)halt(8);
        if(base>=start&&base+size<=start+bytes)found=1;
    }
    if(!found)halt(33);
    if(overlap(base,size,initrd,rdlen)||overlap(base,size,(uintptr_t)incoming,fdt_totalsize(incoming)))halt(34);
    reserved(incoming,base,size);
}
static char *trace_field(char *p,const char *key,uint64_t value) {
    while(*key)*p++=*key++;
    for(int i=60;i>=0;i-=4)*p++="0123456789abcdef"[(value>>i)&15];
    return p;
}
static int nomap_covers(const void *dt,uint64_t base,uint64_t size) {
    int parent=fdt_path_offset(dt,"/reserved-memory"),n;
    if(parent<0)halt(29);
    fdt_for_each_subnode(n,dt,parent) {
        int len;
        if(!fdt_getprop(dt,n,"no-map",&len))continue;
        const fdt32_t *r=fdt_getprop(dt,n,"reg",&len);
        if(!r)continue;
        for(int i=0;i<len/4;i+=4)
            if(base>=be64(r+i)&&base+size<=be64(r+i)+be64(r+i+2))return 1;
    }
    return 0;
}
static void preserve_nomap(const void *source,int node,void *dest,const fdt32_t *reg,int len) {
    int plen,needed=0;
    if(!fdt_getprop(source,node,"no-map",&plen))return;
    for(int i=0;i<len/4;i+=4)
        if(!nomap_covers(dest,be64(reg+i),be64(reg+i+2)))needed=1;
    if(!needed)return;
    const char *old=fdt_get_name(source,node,&plen);
    if(!old||plen>80)halt(30);
    char name[85]="abl-";
    memcpy(name+4,old,plen+1);
    int parent=fdt_path_offset(dest,"/reserved-memory");
    int new=fdt_add_subnode(dest,parent,name);
    if(new<0||fdt_setprop(dest,new,"reg",reg,len)||fdt_setprop(dest,new,"no-map",NULL,0))halt(31);
}
static void preserve_reservations(const void *source,void *dest) {
    int parent=fdt_path_offset(source,"/reserved-memory"),n;
    if(parent>=0) {
        fdt_for_each_subnode(n,source,parent) {
            int len;const fdt32_t *r=fdt_getprop(source,n,"reg",&len);
            if(!r)continue;
            if(len%16)halt(26);
            for(int i=0;i<len/4;i+=4) {
                uint64_t base=be64(r+i),size=be64(r+i+2);
                if(size&&fdt_add_mem_rsv(dest,base,size))halt(27);
            }
            preserve_nomap(source,n,dest,r,len);
        }
    }
    for(int i=0;i<fdt_num_mem_rsv(source);i++) {
        uint64_t base,size;
        if(fdt_get_mem_rsv(source,i,&base,&size)||fdt_add_mem_rsv(dest,base,size))halt(28);
    }
}
uint64_t bridge(const void *incoming) {
    uint64_t el,sctlr;
    asm volatile("mrs %0, CurrentEL":"=r"(el));
    if(el==8)asm volatile("mrs %0, sctlr_el2":"=r"(sctlr));
    else if(el==4)asm volatile("mrs %0, sctlr_el1":"=r"(sctlr));
    else halt(11);
    if(sctlr&5)halt(12);
    if(fdt_check_header(incoming)||fdt_totalsize(incoming)>0x100000||fdt_check_full(incoming,fdt_totalsize(incoming)))halt(13);
    if(fdt_check_full(native_dtb,native_dtb_end-native_dtb))halt(14);
    if(fdt_address_cells(incoming,0)!=2||fdt_size_cells(incoming,0)!=2)halt(15);
    int len,chosen=fdt_path_offset(incoming,"/chosen");
    const void *p=fdt_getprop(incoming,chosen,"linux,initrd-start",&len);
    if(!p)halt(16);
    uint64_t rd=address(p,len);
    p=fdt_getprop(incoming,chosen,"linux,initrd-end",&len);
    if(!p)halt(17);
    uint64_t end=address(p,len);
    if(end<=rd)halt(18);
    const fdt32_t *ram=fdt_getprop(incoming,memory_node(incoming),"reg",&len);
    if(!ram||!len||len%16)halt(19);
    source_range(incoming,ram,len,rd,end-rd);
    uint64_t image_size=*(const uint64_t *)(native_image+16);
    uint64_t text_offset=*(const uint64_t *)(native_image+8);
    size_t bytes=native_image_end-native_image;
    if(text_offset||image_size<bytes||image_size>DTB_ADDR-KERNEL_ADDR)halt(20);
    destination(incoming,ram,len,KERNEL_ADDR,image_size,rd,end-rd);
    destination(incoming,ram,len,DTB_ADDR,DTB_SPACE,rd,end-rd);
    prepare_range_poc(KERNEL_ADDR,image_size);
    prepare_range_poc(DTB_ADDR,DTB_SPACE);
    void *dt=(void *)DTB_ADDR;
    if(fdt_open_into(native_dtb,dt,DTB_SPACE))halt(21);
    int mem=memory_node(dt);
    if(fdt_setprop(dt,mem,"reg",ram,len))halt(22);
    int dst=fdt_path_offset(dt,"/chosen");
    const char *names[]={"linux,initrd-start","linux,initrd-end","kaslr-seed","rng-seed"};
    for(unsigned i=0;i<4;i++) {
        p=fdt_getprop(incoming,chosen,names[i],&len);
        if(p&&fdt_setprop(dt,dst,names[i],p,len))halt(23);
    }
    const char cmdline[]="rdinit=/init console=tty0 loglevel=8 ignore_loglevel printk.time=1 keep_bootcon clk_ignore_unused pd_ignore_unused panic=0";
    if(fdt_setprop(dt,dst,"bootargs",cmdline,sizeof(cmdline)))halt(24);
    uint64_t daif;
    asm volatile("mrs %0, DAIF":"=r"(daif));
    char trace[192];
    char *q=trace_field(trace,"LEMON_BOOTSHIM_V3 base=0x",(uintptr_t)_start);
    q=trace_field(q," end=0x",(uintptr_t)wrapper_end);
    q=trace_field(q," el=0x",el>>2);
    q=trace_field(q," sctlr=0x",sctlr);
    q=trace_field(q," daif=0x",daif);
    *q=0;
    if(fdt_setprop(dt,dst,"xiaomi,bootshim-info",trace,q-trace+1))halt(35);
    preserve_reservations(incoming,dt);
    if(fdt_pack(dt)||fdt_check_full(dt,fdt_totalsize(dt)))halt(25);
    memcpy((void *)KERNEL_ADDR,native_image,bytes);
    memset((void *)(KERNEL_ADDR+bytes),0,image_size-bytes);
    clean_range_poc(KERNEL_ADDR,image_size);
    clean_range_poc(DTB_ADDR,DTB_SPACE);
    return DTB_ADDR;
}
