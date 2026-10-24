// Direct original via stamp (0x080657b8). Only allocation/release and warning
// boundaries are supplied by the harness; all numerical instructions and
// constants remain intact. Bounded records and guarded matrix cells.
#include "asitic/impedance.hpp"
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
 boundary(0x804ab74,reinterpret_cast<unsigned>(&probe_allocate));
 boundary(0x804ac74,reinterpret_cast<unsigned>(&probe_release));
 fd=open(argv[3],0);if(fd<0)return 20;unsigned n;
 if(read(fd,&n,4)!=4||n<1||n>65536)return 21;
 unsigned short control_before;asm volatile("fnstcw %0":"=m"(control_before));write(1,&control_before,2);
 for(unsigned i=0;i<n;i++){
  double p[9];unsigned used=0;while(used<sizeof(p)){int got=read(fd,reinterpret_cast<u8*>(p)+used,sizeof(p)-used);if(got<=0)return 23;used+=got;}
  asitic::ConductorSegment segment{};segment.endpoints[2]=p[1];segment.endpoints[5]=p[2];
  segment.metal=3;segment.width_count=int(p[5]);segment.thickness_count=int(p[6]);
  asitic::ShapeFilamentList shape{};shape.first=&segment;
  asitic::ViaLayer via{};via.perimeter_step=p[3];via.resistance=p[4];
  int index=1;asitic::InductanceContext context{};context.shape=&shape;context.frequency=p[0];context.via_count=1;context.via_indices=&index;
  *reinterpret_cast<int*>(0x80d8904)=3;*reinterpret_cast<asitic::ViaLayer**>(0x80d8914)=&via;
  C matrix[9],before[9];for(int j=0;j<9;j++)matrix[j]=before[j]={.125*(j+1),-.25*j};matrix[4]=before[4]={p[7],p[8]};
  struct Descriptor{C* data;unsigned reserved[4];int stride;} descriptor{matrix,{},3},saved=descriptor;
  heap_used=0;warnings=0;const unsigned status=reinterpret_cast<unsigned(*)(Descriptor*,const asitic::InductanceContext*)>(0x80657b8)(&descriptor,&context)&255;
  if(__builtin_memcmp(&descriptor,&saved,sizeof(saved))||warnings)return 24;
  for(int j=0;j<9;j++)if(j!=4&&__builtin_memcmp(matrix+j,before+j,sizeof(C)))return 25;
  write(1,&status,4);write(1,matrix+4,16);
 }
 unsigned short control_after;asm volatile("fnstcw %0":"=m"(control_after));write(1,&control_after,2);
 close(fd);return 0;
}
asm(".text\n.global _start\n_start:\n"
 "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
 "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
 "call __libc_start_main\nhlt\n");
