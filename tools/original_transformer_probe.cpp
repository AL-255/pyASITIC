// Original folded nodes, transformer inverse and model extraction.
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

 boundary(0x804ab74,reinterpret_cast<unsigned>(&probe_allocate));
 boundary(0x804ac74,reinterpret_cast<unsigned>(&probe_release));
 boundary(0x804c070,reinterpret_cast<unsigned>(&probe_status));
 *reinterpret_cast<u8*>(0x80ce5c0)=0;*reinterpret_cast<u8*>(0x80ce5c2)=0;
 fd=open(argv[3],0);if(fd<0)return 20;unsigned mode,n;
 if(read(fd,&mode,4)!=4||read(fd,&n,4)!=4||mode>1||n>65||(mode&&n<1))return 21;
 double frequency;if(read(fd,&frequency,8)!=8)return 22;
 static C cap[65*65],ind[65*65],y[4];
 const unsigned y_addresses[]={0x80d8da8,0x80d8db8,0x80d8dd8,0x80d8de8};
 unsigned status=1;
 if(mode){
  C* arrays[]={cap,ind};unsigned expected=n*n*sizeof(C);
  for(C* array:arrays){unsigned used=0;while(used<expected){int got=read(fd,reinterpret_cast<u8*>(array)+used,expected-used);if(got<=0)return 23;used+=got;}}
  status=reinterpret_cast<int(*)(C*,C*,int)>(0x8053e00)(cap,ind,n)&255;
 }else{
  unsigned used=0;while(used<sizeof(y)){int got=read(fd,reinterpret_cast<u8*>(y)+used,sizeof(y)-used);if(got<=0)return 24;used+=got;}
  for(unsigned i=0;i<4;i++)*reinterpret_cast<C*>(y_addresses[i])=y[i];
 }
 close(fd);write(1,&status,4);
 if(mode)write(1,cap,n*n*sizeof(C));
 for(unsigned address:y_addresses)write(1,reinterpret_cast<void*>(address),sizeof(C));
 const unsigned z_addresses[]={0x80d8cc8,0x80d8cb8,0x80d8c98,0x80d8c88};
 reinterpret_cast<void(*)()>(0x808800c)();
 for(unsigned address:z_addresses)write(1,reinterpret_cast<void*>(address),sizeof(C));
 reinterpret_cast<void(*)(double)>(0x8089cb0)(frequency);
 const unsigned m_addresses[]={0x80d8828,0x80d8830,0x80d8848,0x80d8850,0x80d8840,0x80d8868,0x80d8838};
 for(unsigned address:m_addresses)write(1,reinterpret_cast<void*>(address),8);
 for(unsigned address:z_addresses)write(1,reinterpret_cast<void*>(address),sizeof(C));

 return 0;
}
asm(".text\n.global _start\n_start:\n"
 "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
 "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
 "call __libc_start_main\nhlt\n");
