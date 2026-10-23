// Intact coefficient loop in original CAP driver at 0x08052c50.
// Contact preparation supplies an empty list; cache-load entry captures the
// completed coefficients and exits. No coefficient/weight arithmetic is patched.
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
static C captured[256];static int layer_count;
extern "C" void _exit(int);
extern "C" int prepare_no_contacts(){*reinterpret_cast<unsigned*>(0x80ce9a4)=0;return 1;}
extern "C" void capture_before_cache(){write(1,captured,layer_count*sizeof(C));_exit(0);}
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

 boundary(0x8053580,reinterpret_cast<unsigned>(&prepare_no_contacts));
 boundary(0x808c0bc,reinterpret_cast<unsigned>(&capture_before_cache));
 *reinterpret_cast<u8*>(0x80ce5c0)=0;
 #pragma pack(push,4)
 struct Layer{u8 prefix[12];double rho,height,thickness;u8 suffix[4];};
 #pragma pack(pop)
 static_assert(sizeof(Layer)==40);static Layer layers[256];
 fd=open(argv[3],0);if(fd<0)return 20;
 if(read(fd,&layer_count,4)!=4||layer_count<1||layer_count>256)return 21;
 double frequency;if(read(fd,&frequency,8)!=8)return 22;
 for(int i=0;i<layer_count;i++){
  double values[2];if(read(fd,values,16)!=16)return 23;
  layers[i].rho=values[0];__builtin_memcpy(layers[i].prefix+4,values+1,8);
 }
 close(fd);
 *reinterpret_cast<unsigned*>(0x80d890c)=reinterpret_cast<unsigned>(layers);
 *reinterpret_cast<int*>(0x80d8900)=layer_count;
 *reinterpret_cast<unsigned*>(0x80d8ac8)=reinterpret_cast<unsigned>(captured);
 reinterpret_cast<int(*)(void*,void*,void*,double)>(0x8052c50)(nullptr,nullptr,nullptr,frequency);
 return 30;

 return 0;
}
asm(".text\n.global _start\n_start:\n"
 "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
 "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
 "call __libc_start_main\nhlt\n");
