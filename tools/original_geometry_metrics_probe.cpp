// Intact original GEOM and METALAREA on supplied primary segment records.
// Only the nonnumerical sprintf/status sinks are replaced. The format sink
// copies the actual variadic GEOM F64 arguments without recalculating them.
extern "C" int open(const char*,int,...);extern "C" int read(int,void*,unsigned);extern "C" int close(int);extern "C" int write(int,const void*,unsigned);extern "C" void* mmap(void*,unsigned,int,int,int,int);
typedef unsigned u32;typedef unsigned short u16;typedef unsigned char u8;
struct Header{u8 ident[16];u16 type,machine;u32 version,entry,phoff,shoff,flags;u16 ehsize,phentsize,phnum,shentsize,shnum,shstrndx;};
struct PH{u32 type,offset,vaddr,paddr,filesz,memsz,flags,align;};
static u8 file[2*1024*1024],shape[0xbc],segments[128][0xf0];static double geom[2];static unsigned reports;
extern "C" void probe_status(const char*){}
extern "C" int probe_format(char* out,const char* format,...){
 const char* prefix="Total length =";unsigned i=0;while(prefix[i]&&prefix[i]==format[i])i++;
 if(!prefix[i]){__builtin_va_list args;__builtin_va_start(args,format);geom[0]=__builtin_va_arg(args,double);geom[1]=__builtin_va_arg(args,double);__builtin_va_end(args);reports++;}
 out[0]=0;return 0;
}
static void boundary(unsigned address,unsigned destination){u8* p=reinterpret_cast<u8*>(address);p[0]=0xe9;*reinterpret_cast<unsigned*>(p+1)=destination-address-5;}
static bool receive(int fd,void* p,unsigned size){unsigned used=0;while(used<size){int got=read(fd,static_cast<u8*>(p)+used,size-used);if(got<=0)return false;used+=got;}return true;}
extern "C" int probe_main(int argc,char** argv){
 if(argc!=3)return 8;int fd=open(argv[1],0);if(fd<0)return 2;
 unsigned size=0;for(;;){int got=read(fd,file+size,sizeof(file)-size);if(got<0)return 3;if(!got)break;size+=got;if(size==sizeof(file))return 4;}close(fd);
 if(mmap(reinterpret_cast<void*>(0x8048000),0x95000,7,0x100022,-1,0)!=reinterpret_cast<void*>(0x8048000))return 5;
 Header* h=reinterpret_cast<Header*>(file);PH* ph=reinterpret_cast<PH*>(file+h->phoff);if(h->machine!=3||h->type!=2||h->phnum>16)return 6;
 for(unsigned i=0;i<h->phnum;i++)if(ph[i].type==1){if(ph[i].offset+ph[i].filesz>size||ph[i].vaddr<0x8048000||ph[i].vaddr+ph[i].memsz>0x80dd000)return 7;u8* to=reinterpret_cast<u8*>(ph[i].vaddr);for(unsigned j=0;j<ph[i].filesz;j++)to[j]=file[ph[i].offset+j];}
 boundary(0x804ae04,reinterpret_cast<unsigned>(&probe_format));boundary(0x804c070,reinterpret_cast<unsigned>(&probe_status));
 shape[0]='A';*reinterpret_cast<unsigned*>(shape+0x50)=21;
 fd=open(argv[2],0);if(fd<0)return 20;unsigned cases;if(!receive(fd,&cases,4)||cases<1||cases>65536)return 21;
 unsigned short before;asm volatile("fnstcw %0":"=m"(before));write(1,&before,2);
 for(unsigned c=0;c<cases;c++){
  unsigned count;if(!receive(fd,&count,4)||count>128)return 22;
  for(unsigned i=0;i<count;i++){
   double p[7];if(!receive(fd,p,sizeof(p)))return 23;
   for(unsigned k=0;k<48;k++)segments[i][k]=reinterpret_cast<u8*>(p)[k];for(unsigned k=0;k<8;k++)segments[i][0xcc+k]=reinterpret_cast<u8*>(p+6)[k];
   *reinterpret_cast<unsigned*>(segments[i]+0xec)=i+1<count?reinterpret_cast<unsigned>(segments[i+1]):0;
  }
  *reinterpret_cast<unsigned*>(shape+0xa8)=count?reinterpret_cast<unsigned>(segments[0]):0;reports=0;
  reinterpret_cast<void(*)(const void*)>(0x804c620)(shape);if(reports!=1)return 24;
  const long double metal=reinterpret_cast<long double(*)(const void*)>(0x804ee74)(shape);double stored=metal;
  write(1,geom,16);write(1,&stored,8);write(1,&metal,10);
 }
 unsigned short after;asm volatile("fnstcw %0":"=m"(after));write(1,&after,2);close(fd);return 0;
}
asm(".text\n.global _start\n_start:\n"
 "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
 "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
 "call __libc_start_main\nhlt\n");
