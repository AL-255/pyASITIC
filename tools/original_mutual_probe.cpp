// Intact original self/cross-section/separation/parallel/segment routines.
// Modes 5-11 independently execute the matching native x87 math instructions.
// Only the nonnumerical status sink is replaced; numerical instructions,
// constants and legacy-complex imports remain intact.
// File payload uses the same bounded double records as the browser kernel.
// Original legacy-complex DSO imports are resolved without substituting
// numerical functions. No numerical
// instructions or data are patched. Link the probe at 0x10000000.
extern "C" int printf(const char*,...);
extern "C" int atoi(const char*);
extern "C" double atof(const char*);
extern "C" int open(const char*,int,...);
extern "C" int read(int,void*,unsigned);
extern "C" int close(int);
extern "C" int write(int,const void*,unsigned);
extern "C" void* mmap(void*,unsigned,int,int,int,int);
typedef unsigned u32;typedef unsigned short u16;typedef unsigned char u8;
struct Header{u8 ident[16];u16 type,machine;u32 version,entry,phoff,shoff,flags;u16 ehsize,phentsize,phnum,shentsize,shnum,shstrndx;};
struct PH{u32 type,offset,vaddr,paddr,filesz,memsz,flags,align;};
struct C{double re,im;};
static u8 file[2*1024*1024];
static u8 heap[1024*1024];static unsigned heap_used;
extern "C" void* probe_allocate(unsigned n){unsigned size=(n+15)&~15u;if(size>sizeof(heap)-heap_used)return nullptr;void* p=heap+heap_used;heap_used+=size?size:16;return p;}
extern "C" void probe_release(void*){}
static unsigned warnings;extern "C" void probe_status(const char*){warnings++;}
static void boundary(unsigned address,unsigned destination){u8* p=reinterpret_cast<u8*>(address);p[0]=0xe9;*reinterpret_cast<unsigned*>(p+1)=destination-address-5;}
extern "C" int probe_main(int argc,char** argv){
 if(argc!=4)return 8;
 int fd=open(argv[1],0);if(fd<0)return 2;
 unsigned size=0;for(;;){int got=read(fd,file+size,sizeof(file)-size);if(got<0)return 3;if(!got)break;size+=got;if(size==sizeof(file))return 4;}close(fd);
 void* mapped=mmap(reinterpret_cast<void*>(0x8048000),0x95000,7,0x100022,-1,0);if(mapped!=reinterpret_cast<void*>(0x8048000))return 5;
 Header* h=reinterpret_cast<Header*>(file);PH* ph=reinterpret_cast<PH*>(file+h->phoff);
 if(h->machine!=3||h->type!=2||h->phnum>16)return 6;
 for(unsigned i=0;i<h->phnum;i++)if(ph[i].type==1){
  if(ph[i].offset+ph[i].filesz>size||ph[i].vaddr<0x8048000||ph[i].vaddr+ph[i].memsz>0x80dd000)return 7;
  u8* to=reinterpret_cast<u8*>(ph[i].vaddr);for(unsigned j=0;j<ph[i].filesz;j++)to[j]=file[ph[i].offset+j];
 }
 fd=open(argv[2],0);if(fd<0)return 10;
 size=0;for(;;){int got=read(fd,file+size,sizeof(file)-size);if(got<0)return 11;if(!got)break;size+=got;if(size==sizeof(file))return 13;}close(fd);
 if(mmap(reinterpret_cast<void*>(0x30000000),0x42000,7,0x100022,-1,0)!=reinterpret_cast<void*>(0x30000000))return 12;
 h=reinterpret_cast<Header*>(file);ph=reinterpret_cast<PH*>(file+h->phoff);
 if(h->type!=3||h->machine!=3||h->phnum>16)return 14;
 for(unsigned i=0;i<h->phnum;i++)if(ph[i].type==1){if(ph[i].offset+ph[i].filesz>size||ph[i].vaddr+ph[i].memsz>0x42000)return 15;u8* to=reinterpret_cast<u8*>(0x30000000+ph[i].vaddr);for(unsigned j=0;j<ph[i].filesz;j++)to[j]=file[ph[i].offset+j];}
 const unsigned bindings[][2]={{0x80d797c,0x1d618},{0x80d7994,0x1d3c0},{0x80d79ec,0x1daf4},{0x80d7a28,0x1d6fc},{0x80d7a50,0x1d4cc},{0x80d7aa0,0x1dbd0},{0x80d7af4,0x1d45c}};
 for(const auto& b:bindings)*reinterpret_cast<unsigned*>(b[0])=0x30000000+b[1];



 boundary(0x804c070,reinterpret_cast<unsigned>(&probe_status));
 fd=open(argv[3],0);if(fd<0)return 20;unsigned n;
 if(read(fd,&n,4)!=4||n<1||n>65536)return 21;
 unsigned short control_before;asm volatile("fnstcw %0":"=m"(control_before));write(1,&control_before,2);
 for(unsigned i=0;i<n;i++){
  unsigned mode;if(read(fd,&mode,4)!=4||mode>11)return 22;
  double p[17];unsigned used=0;while(used<sizeof(p)){int got=read(fd,reinterpret_cast<u8*>(p)+used,sizeof(p)-used);if(got<=0)return 23;used+=got;}
  int status=0;long double value=0;warnings=0;
  if(mode==0)value=reinterpret_cast<long double(*)(double,double)>(0x8064308)(p[0],p[1]);
  if(mode==1)value=reinterpret_cast<long double(*)(double,double)>(0x80b3c94)(p[0],p[1]);
  if(mode==2)value=reinterpret_cast<long double(*)(double,double,double,double,double,double)>(0x8063ca0)(p[0],p[1],p[2],p[3],p[4],p[5]);
  if(mode==3){double out=423.;status=reinterpret_cast<int(*)(const double*,const double*,double*,double)>(0x8062230)(p,p+8,&out,p[16]);value=out;}
  if(mode==4){double out=423.;status=reinterpret_cast<int(*)(const double*,const double*,double*)>(0x8061110)(p,p+8,&out);value=out;}
  if(mode>=5){
   long double x=p[0];if(p[2]==1)x=x/p[1];if(p[2]==2)x=x+p[1];if(p[2]==3)x=x*p[1];
   if(mode==5)asm("fldln2; fxch; fyl2x":"=t"(value):"0"(x):"st(1)");
   if(mode==6){long double one=1;asm("fpatan":"=t"(value):"0"(one),"u"(x):"st(1)");}
   if(mode==7){
    long double log2e;asm("fldl2e":"=t"(log2e));const long double e=x*log2e;long double integer;
    asm("frndint":"=t"(integer):"0"(e));const long double fraction=e-integer;long double part;
    asm("f2xm1":"=t"(part):"0"(fraction));part+=1;
    asm("fscale":"=t"(value):"0"(part),"u"(integer));
   }
   if(mode==8){const long double yy=p[0],xx=p[1];asm("fpatan":"=t"(value):"0"(xx),"u"(yy):"st(1)");}
   if(mode==9)asm("fcos":"=t"(value):"0"(x));
   if(mode==10)asm("fsin":"=t"(value):"0"(x));
   if(mode==11){
    long double a;asm("fabs":"=t"(a):"0"(x));const long double u=-(a+a)/(a+1.0L);long double absolute;asm("fabs":"=t"(absolute):"0"(u));
    long double logarithm;const long double crossover=0x95f619980c4336f8p-65L;
    if(absolute>=crossover){const long double shifted=1.0L+u;asm("fldln2; fxch; fyl2x":"=t"(logarithm):"0"(shifted):"st(1)");}
    else asm("fldln2; fxch; fyl2xp1":"=t"(logarithm):"0"(u):"st(1)");
    value=(-.5L*logarithm)*(x>=0?1.L:-1.L);
   }
  }
  double rounded=value;write(1,&status,4);write(1,&rounded,8);write(1,&value,10);write(1,&warnings,4);
 }
 unsigned short control_after;asm volatile("fnstcw %0":"=m"(control_after));write(1,&control_after,2);
 close(fd);return 0;
}
asm(".text\n.global _start\n_start:\n"
 "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
 "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
 "call __libc_start_main\nhlt\n");
