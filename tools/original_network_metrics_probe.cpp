// Intact original Pi metrics, impedances and scattering with original DSO imports.
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
static u8 heap[8*1024*1024];static unsigned heap_used;
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

 boundary(0x804c070,reinterpret_cast<unsigned>(&probe_status));
 fd=open(argv[3],0);if(fd<0)return 20;unsigned count;
 if(read(fd,&count,4)!=4||count<1||count>65536)return 21;
 unsigned short before;asm volatile("fnstcw %0":"=m"(before));write(1,&before,2);
 const unsigned y_addresses[]={0x80d8da8,0x80d8db8,0x80d8dd8,0x80d8de8};
 const unsigned s_addresses[]={0x80d8d58,0x80d8d28,0x80d8d48,0x80d8d18};
 for(unsigned i=0;i<count;i++){
  unsigned mode;if(read(fd,&mode,4)!=4||mode>1)return 22;
  double p[25];unsigned used=0;while(used<sizeof(p)){int got=read(fd,reinterpret_cast<u8*>(p)+used,sizeof(p)-used);if(got<=0)return 23;used+=got;}
  const int port=int(p[1]),differential=int(p[2]);
  for(unsigned j=0;j<4;j++)*reinterpret_cast<C*>(y_addresses[j])={p[5+2*j],p[6+2*j]};
  if(!mode)reinterpret_cast<void(*)(double)>(0x8089e40)(p[0]);
  else for(unsigned j=0;j<12;j++)*reinterpret_cast<double*>(0x80d8820+8*j)=p[13+j];
  write(1,reinterpret_cast<void*>(0x80d8820),96);
  const long double scalars[]={reinterpret_cast<long double(*)(int)>(0x804e354)(0),reinterpret_cast<long double(*)(int)>(0x804e354)(1),reinterpret_cast<long double(*)()>(0x804ec50)()};
  for(auto x:scalars){double value=x;write(1,&value,8);}
  const C z=reinterpret_cast<C(*)(char,int)>(0x804e8b0)(differential,port);write(1,&z,16);
  const long double imag=reinterpret_cast<long double(*)(int)>(0x804e7c0)(differential);double value=imag;write(1,&value,8);
  const C load{p[3],p[4]},terminated=reinterpret_cast<C(*)(C,int)>(0x804e9b0)(load,port);write(1,&terminated,16);
  reinterpret_cast<void(*)()>(0x8087d14)();for(unsigned address:s_addresses)write(1,reinterpret_cast<void*>(address),16);
  for(const auto& x:scalars)write(1,&x,10);write(1,&imag,10);
 }
 unsigned short after;asm volatile("fnstcw %0":"=m"(after));write(1,&after,2);close(fd);return 0;
}
asm(".text\n.global _start\n_start:\n"
 "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
 "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
 "call __libc_start_main\nhlt\n");
