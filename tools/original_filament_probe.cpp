// Original filament interpolation, 0x0806597c. No numerical instructions are changed.
// Only allocation, deletion and status boundaries are replaced; numerical
// instructions, constants and legacy-complex imports remain intact.
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
extern "C" void probe_status(const char*){}
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


 fd=open(argv[3],0);if(fd<0)return 20;unsigned n;
 if(read(fd,&n,4)!=4||n<1||n>4096)return 21;
 struct Metal {u8 prefix[0xb0];double thickness,resistance;u8 suffix[0x2c];} __attribute__((packed,aligned(4)));
 struct Filament {double values[8];int metal;} __attribute__((packed,aligned(4)));
 static Metal metals[3];*reinterpret_cast<Metal**>(0x80d8910)=metals;
 for(unsigned i=0;i<n;i++){
  double p[26];unsigned used=0;while(used<sizeof(p)){int got=read(fd,reinterpret_cast<u8*>(p)+used,sizeof(p)-used);if(got<=0)return 22;used+=got;}
  u8 segment[0xf0]={};const unsigned offsets[]={0x88,0xa0,0x44,0x5c};
  for(unsigned j=0;j<4;j++)for(unsigned k=0;k<3;k++)*reinterpret_cast<double*>(segment+offsets[j]+8*k)=p[3*j+k];
  *reinterpret_cast<double*>(segment+0xcc)=p[12];*reinterpret_cast<double*>(segment+0xd4)=p[13];
  *reinterpret_cast<int*>(segment+0xdc)=int(p[25]);metals[int(p[25])].thickness=p[14];
  *reinterpret_cast<double*>(0x80ce588)=p[17];*reinterpret_cast<int*>(0x80ce5a8)=int(p[18]);
  Filament result{};
  reinterpret_cast<void(*)(const void*,Filament*,const double*,int,int,int,int,int,int)>(0x806597c)(segment,&result,p+15,int(p[19]),int(p[20]),int(p[21]),int(p[22]),int(p[23]),int(p[24]));
  write(1,result.values,64);double metal=result.metal;write(1,&metal,8);
 }
 close(fd);return 0;
}
asm(".text\n.global _start\n_start:\n"
 "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
 "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
 "call __libc_start_main\nhlt\n");
