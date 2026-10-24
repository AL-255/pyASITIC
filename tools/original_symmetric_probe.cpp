// Original upper symmetric factor (0x0809bcf8) and inverse (0x08095bf8).
// Original legacy-complex DSO imports are resolved without substituting
// numerical functions. No numerical
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
 fd=open(argv[2],0);if(fd<0)return 10;
 size=0;for(;;){int got=read(fd,file+size,sizeof(file)-size);if(got<0)return 11;if(!got)break;size+=got;if(size==sizeof(file))return 13;}close(fd);
 if(mmap(reinterpret_cast<void*>(0x30000000),0x42000,7,0x100022,-1,0)!=reinterpret_cast<void*>(0x30000000))return 12;
 h=reinterpret_cast<Header*>(file);ph=reinterpret_cast<PH*>(file+h->phoff);
 if(h->type!=3||h->machine!=3||h->phnum>16)return 14;
 for(unsigned i=0;i<h->phnum;i++)if(ph[i].type==1){if(ph[i].offset+ph[i].filesz>size||ph[i].vaddr+ph[i].memsz>0x42000)return 15;u8* to=reinterpret_cast<u8*>(0x30000000+ph[i].vaddr);for(unsigned j=0;j<ph[i].filesz;j++)to[j]=file[ph[i].offset+j];}
 const unsigned bindings[][2]={{0x80d797c,0x1d618},{0x80d7994,0x1d3c0},{0x80d79ec,0x1daf4},{0x80d7a28,0x1d6fc},{0x80d7a50,0x1d4cc},{0x80d7aa0,0x1dbd0},{0x80d7af4,0x1d45c}};
 for(const auto& b:bindings)*reinterpret_cast<unsigned*>(b[0])=0x30000000+b[1];
 int n=atoi(argv[3]),stride=atoi(argv[4]);if(n<1||n>512||stride<n||n*stride>263168||argc!=6)return 20;
 static C data[263168],work[512],saved[263168];static int pivots[512];
 fd=open(argv[5],0);if(fd<0)return 21;unsigned used=0,expected=n*stride*sizeof(C);
 while(used<expected){int got=read(fd,reinterpret_cast<u8*>(data)+used,expected-used);if(got<=0)return 22;used+=got;}close(fd);
 for(int i=0;i<n*stride;i++)saved[i]=data[i];
 char upper='U';int info=0;
 using Factor=int(*)(char*,int*,C*,int*,int*,int*);
 using Inverse=int(*)(char*,int*,C*,int*,int*,C*,int*);
 reinterpret_cast<Factor>(0x809bcf8)(&upper,&n,data,&stride,pivots,&info);
 printf("S %d\n",info);printf("P ");for(int i=0;i<n;i++)printf("%d ",pivots[i]);printf("\nF ");
 for(int i=0;i<n;i++)for(int j=0;j<n;j++)printf("%.17g %.17g ",data[j*stride+i].re,data[j*stride+i].im);printf("\n");
 if(!info){reinterpret_cast<Inverse>(0x8095bf8)(&upper,&n,data,&stride,pivots,work,&info);printf("T %d\nI ",info);for(int i=0;i<n;i++)for(int j=0;j<n;j++)printf("%.17g %.17g ",data[j*stride+i].re,data[j*stride+i].im);printf("\n");}
 int padding=1;for(int j=0;j<n;j++)for(int i=n;i<stride;i++){
 const u8* a=reinterpret_cast<const u8*>(&data[j*stride+i]);const u8* b=reinterpret_cast<const u8*>(&saved[j*stride+i]);for(unsigned k=0;k<sizeof(C);k++)if(a[k]!=b[k])padding=0;
 }printf("G %d\n",padding);
 return 0;
}
asm(".text\n.global _start\n_start:\n"
 "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
 "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
 "call __libc_start_main\nhlt\n");
