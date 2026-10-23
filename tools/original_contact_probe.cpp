// Original contact-potential instructions at 0x080901c0.
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
extern "C" void* mmap(void*,unsigned,int,int,int,int);
typedef unsigned u32;typedef unsigned short u16;typedef unsigned char u8;
struct Header{u8 ident[16];u16 type,machine;u32 version,entry,phoff,shoff,flags;u16 ehsize,phentsize,phnum,shentsize,shnum,shstrndx;};
struct PH{u32 type,offset,vaddr,paddr,filesz,memsz,flags,align;};
struct C{double re,im;};
static u8 file[2*1024*1024];
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
 for(const auto& b:bindings)*reinterpret_cast<unsigned*>(b[0])=0x30000000+b[1]; static double config[4096],depths[257];static C coefficients[256],tables[67073];
 #pragma pack(push,4)
 struct Metal{u8 prefix[176];double thickness,resistance;u8 suffix[44];};
 struct Contact{u8 prefix[32];int x0,x1,y0,y1,metal,index;unsigned next;};
 #pragma pack(pop)
 static_assert(sizeof(Metal)==236);static_assert(sizeof(Contact)==60);
 static Metal metals[256];static Contact contacts[256];
 fd=open(argv[3],0);if(fd<0)return 20;unsigned sizes[2];if(read(fd,sizes,8)!=8)return 21;
 if(sizes[0]>4096||sizes[1]>67073)return 22;
 unsigned used=0,bytes=sizes[0]*8;while(used<bytes){int got=read(fd,reinterpret_cast<u8*>(config)+used,bytes-used);if(got<=0)return 23;used+=got;}
 used=0;bytes=sizes[1]*16;while(used<bytes){int got=read(fd,reinterpret_cast<u8*>(tables)+used,bytes-used);if(got<=0)return 24;used+=got;}close(fd);
 int n=config[1],nx=config[2],ny=config[3],nm=config[4],nl=config[5],lo=config[6],hi=config[7];
 if(n<1||n>256||nx<2||nx>256||ny<2||ny>256||nm<1||nm>256||nl<1||nl>256)return 25;
 int offset=16;for(int i=0;i<n;i++){contacts[i].x0=config[offset++];contacts[i].x1=config[offset++];contacts[i].y0=config[offset++];contacts[i].y1=config[offset++];contacts[i].metal=config[offset++];}
 for(int i=0;i<nm;i++){int layer=config[offset++];double height=config[offset++];metals[i].thickness=config[offset++];__builtin_memcpy(metals[i].prefix+160,&layer,4);__builtin_memcpy(metals[i].prefix+168,&height,8);}
 for(int i=0;i<nl;i++){coefficients[i]={config[offset],config[offset+1]};offset+=2;}for(int i=0;i<=nl;i++)depths[i]=config[offset++];
 *reinterpret_cast<int*>(0x80ce990)=nx;*reinterpret_cast<int*>(0x80ce994)=ny;
 *reinterpret_cast<double*>(0x80ce980)=config[8];*reinterpret_cast<double*>(0x80ce988)=config[9];
 *reinterpret_cast<unsigned*>(0x80d8910)=reinterpret_cast<unsigned>(metals);*reinterpret_cast<int*>(0x80d8904)=nm;
 *reinterpret_cast<unsigned*>(0x80d8ac8)=reinterpret_cast<unsigned>(coefficients);*reinterpret_cast<unsigned*>(0x80d8918)=reinterpret_cast<unsigned>(depths);
 using Pair=C(*)(const Contact*,const Contact*,const C*,const C*,const C*);
 for(int i=0;i<n;i++)for(int j=0;j<n;j++){
  const int a=contacts[i].metal,b=contacts[j].metal;
  if((a==lo&&b==hi)||(a==hi&&b==lo)){C z=reinterpret_cast<Pair>(0x80901c0)(&contacts[i],&contacts[j],tables,tables+2*nx,tables+2*nx+2*ny);printf("%d %d %.17g %.17g\n",i,j,z.re,z.im);}
 }

 return 0;
}
asm(".text\n.global _start\n_start:\n"
 "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
 "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
 "call __libc_start_main\nhlt\n");
