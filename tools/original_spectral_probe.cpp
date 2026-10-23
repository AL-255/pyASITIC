// Intact original spectral/transfer/table-generation instructions.
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
static u8 heap[16384];
extern "C" void* probe_allocate(unsigned){return heap;}
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
 boundary(0x804bf74,reinterpret_cast<unsigned>(&probe_status));
 static double config[2048],depths[257],requests[7*512];static C coefficients[258],tables[67073],output[512];
 #pragma pack(push,4)
 struct Metal{u8 prefix[176];double thickness,resistance;u8 suffix[44];};
 #pragma pack(pop)
 static_assert(sizeof(Metal)==236);static Metal metals[256];
 fd=open(argv[3],0);if(fd<0)return 20;unsigned sizes[2];if(read(fd,sizes,8)!=8)return 21;
 if(sizes[0]>2048||sizes[1]>512)return 22;
 unsigned used=0,bytes=sizes[0]*8;while(used<bytes){int got=read(fd,reinterpret_cast<u8*>(config)+used,bytes-used);if(got<=0)return 23;used+=got;}
 used=0;bytes=sizes[1]*7*8;while(used<bytes){int got=read(fd,reinterpret_cast<u8*>(requests)+used,bytes-used);if(got<=0)return 24;used+=got;}close(fd);
 int nx=config[1],ny=config[2],nm=config[3],nl=config[4],source=config[5],target=config[6];
 if(nx<2||nx>256||ny<2||ny>256||nm<1||nm>256||nl<1||nl>256)return 25;
 int offset=9;
 for(int i=0;i<nm;i++){int layer=config[offset++];double height=config[offset++];metals[i].thickness=config[offset++];__builtin_memcpy(metals[i].prefix+160,&layer,4);__builtin_memcpy(metals[i].prefix+168,&height,8);}
 for(int i=0;i<nl;i++){coefficients[i+1]={config[offset],config[offset+1]};offset+=2;}
 for(int i=0;i<=nl;i++)depths[i]=config[offset++];
 *reinterpret_cast<int*>(0x80ce990)=nx;*reinterpret_cast<int*>(0x80ce994)=ny;
 *reinterpret_cast<double*>(0x80ce980)=config[7];*reinterpret_cast<double*>(0x80ce988)=config[8];
 *reinterpret_cast<unsigned*>(0x80d8910)=reinterpret_cast<unsigned>(metals);*reinterpret_cast<int*>(0x80d8900)=nl;
 *reinterpret_cast<unsigned*>(0x80d8ac8)=reinterpret_cast<unsigned>(coefficients+1);*reinterpret_cast<unsigned*>(0x80d8918)=reinterpret_cast<unsigned>(depths);
 for(unsigned i=0;i<sizes[1];i++){
  const double* q=requests+7*i;const int kind=q[0],a=q[1],b=q[2],last=q[3];const double k=q[4],sh=q[5],th=q[6];C z;
  switch(kind){
   case 0:z=reinterpret_cast<C(*)(int,double)>(0x808f004)(a,k);break;
   case 1:z=reinterpret_cast<C(*)(int,int,double)>(0x808f80c)(a,last,k);break;
   case 2:z=reinterpret_cast<C(*)(int,double,double)>(0x808f3f0)(a,k,sh);break;
   case 3:z=reinterpret_cast<C(*)(int,int,double,double)>(0x808fc04)(a,last,k,sh);break;
   case 4:z=reinterpret_cast<C(*)(int,int,int,double,double,double)>(0x808cc90)(a,b,last,k,sh,th);break;
   default:z=reinterpret_cast<C(*)(int,int,int,double,double,double)>(0x808dad4)(a,b,last,k,sh,th);
  }
  output[i]=z;
 }
 if(sizes[1])write(1,output,sizes[1]*sizeof(C));
 else{
  reinterpret_cast<void(*)(int,int,C*,C*,C*)>(0x808c350)(source,target,tables+2*nx+2*ny,tables,tables+2*nx);
  const int cells=(nx+1)*(ny+1)>nx*(nx+1)+ny+1?(nx+1)*(ny+1):nx*(nx+1)+ny+1;
  write(1,tables,(2*nx+2*ny+cells)*sizeof(C));
 }
 write(1,depths,(nl+1)*8);

 return 0;
}
asm(".text\n.global _start\n_start:\n"
 "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
 "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
 "call __libc_start_main\nhlt\n");
