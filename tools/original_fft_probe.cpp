// Isolated i386 loader for the original FFT at 0x080912c0. No numerical
// instructions or data are patched. Link the probe at 0x10000000.
extern "C" int printf(const char*,...);
extern "C" int atoi(const char*);
extern "C" double atof(const char*);
extern "C" int open(const char*,int,...);
extern "C" int read(int,void*,unsigned);
extern "C" int close(int);
extern "C" void* mmap(void*,unsigned,int,int,int,int);
typedef unsigned u32;typedef unsigned short u16;typedef unsigned char u8;
struct Header{u8 ident[16];u16 type,machine;u32 version,entry,phoff,shoff,flags;u16 ehsize,phentsize,phnum,shentsize,shnum,shstrndx;};
struct PH{u32 type,offset,vaddr,paddr,filesz,memsz,flags,align;};
struct C{double re,im;};
static u8 file[2*1024*1024];
static C values[8192],scratch[2048];
static void fft(C* a,int n){reinterpret_cast<void(*)(C*,int)>(0x80912c0)(a,n);}
extern "C" int probe_main(int argc,char** argv){
 if(argc<5)return 8;
 int fd=open(argv[1],0);if(fd<0)return 2;
 unsigned size=0;for(;;){int got=read(fd,file+size,sizeof(file)-size);if(got<0)return 3;if(!got)break;size+=got;if(size==sizeof(file))return 4;}close(fd);
 void* mapped=mmap(reinterpret_cast<void*>(0x8048000),0x95000,7,0x100022,-1,0);if(mapped!=reinterpret_cast<void*>(0x8048000))return 5;
 Header* h=reinterpret_cast<Header*>(file);PH* ph=reinterpret_cast<PH*>(file+h->phoff);
 if(h->machine!=3||h->type!=2||h->phnum>16)return 6;
 for(unsigned i=0;i<h->phnum;i++)if(ph[i].type==1){
  if(ph[i].offset+ph[i].filesz>size||ph[i].vaddr<0x8048000||ph[i].vaddr+ph[i].memsz>0x80dd000)return 7;
  u8* to=reinterpret_cast<u8*>(ph[i].vaddr);for(unsigned j=0;j<ph[i].filesz;j++)to[j]=file[ph[i].offset+j];
 }
 int grid=atoi(argv[2]),nx=atoi(argv[3]),ny=atoi(argv[4]);int n=grid?(nx+1)*(ny+1):nx;
 if(n<0||n>8192||argc!=5+2*n||nx>512||ny>512)return 9;
 for(int i=0;i<n;i++)values[i]={atof(argv[5+2*i]),atof(argv[6+2*i])};
 if(!grid)fft(values,nx);
 else{
  int stride=ny+1;
  for(int x=0;x<=nx;x++){
   for(int y=0;y<=ny;y++)scratch[y]=values[x*stride+y];
   for(int y=ny+1;y<2*ny;y++)scratch[y]=values[x*stride+2*ny-y];
   fft(scratch,2*ny);for(int y=0;y<=ny;y++)values[x*stride+y]=scratch[y];
  }
  for(int y=0;y<=ny;y++){
   for(int x=0;x<=nx;x++)scratch[x]=values[x*stride+y];
   for(int x=nx+1;x<2*nx;x++)scratch[x]=values[(2*nx-x)*stride+y];
   fft(scratch,2*nx);for(int x=0;x<=nx;x++)values[x*stride+y]=scratch[x];
  }
 }
 for(int i=0;i<n;i++)printf("%.17g %.17g\n",values[i].re,values[i].im);
 return 0;
}
asm(".text\n.global _start\n_start:\n"
 "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
 "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
 "call __libc_start_main\nhlt\n");
