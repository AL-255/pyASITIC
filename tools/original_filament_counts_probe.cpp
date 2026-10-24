// Intact original set_filament_counts; only allocation/status boundaries replaced.
extern "C" int open(const char*,int,...);extern "C" int read(int,void*,unsigned);extern "C" int close(int);extern "C" int write(int,const void*,unsigned);extern "C" void* mmap(void*,unsigned,int,int,int,int);
typedef unsigned u32;typedef unsigned short u16;typedef unsigned char u8;
struct Header{u8 ident[16];u16 type,machine;u32 version,entry,phoff,shoff,flags;u16 ehsize,phentsize,phnum,shentsize,shnum,shstrndx;};
struct PH{u32 type,offset,vaddr,paddr,filesz,memsz,flags,align;};
static u8 file[2*1024*1024],context[0x50],segment[0xf0],heap[64];static unsigned heap_used;
extern "C" void* probe_allocate(unsigned n){if(n>16||heap_used+16>sizeof(heap))return nullptr;void* p=heap+heap_used;heap_used+=16;return p;}
extern "C" void probe_status(const char*){}
static void boundary(unsigned address,unsigned destination){u8* p=reinterpret_cast<u8*>(address);p[0]=0xe9;*reinterpret_cast<unsigned*>(p+1)=destination-address-5;}
static bool receive(int fd,void* p,unsigned size){unsigned used=0;while(used<size){int got=read(fd,static_cast<u8*>(p)+used,size-used);if(got<=0)return false;used+=got;}return true;}
extern "C" int probe_main(int argc,char** argv){
 if(argc!=3)return 8;int fd=open(argv[1],0);if(fd<0)return 2;
 unsigned size=0;for(;;){int got=read(fd,file+size,sizeof(file)-size);if(got<0)return 3;if(!got)break;size+=got;if(size==sizeof(file))return 4;}close(fd);
 if(mmap(reinterpret_cast<void*>(0x8048000),0x95000,7,0x100022,-1,0)!=reinterpret_cast<void*>(0x8048000))return 5;
 Header* h=reinterpret_cast<Header*>(file);PH* ph=reinterpret_cast<PH*>(file+h->phoff);if(h->machine!=3||h->type!=2||h->phnum>16)return 6;
 for(unsigned i=0;i<h->phnum;i++)if(ph[i].type==1){if(ph[i].offset+ph[i].filesz>size||ph[i].vaddr<0x8048000||ph[i].vaddr+ph[i].memsz>0x80dd000)return 7;u8* to=reinterpret_cast<u8*>(ph[i].vaddr);for(unsigned j=0;j<ph[i].filesz;j++)to[j]=file[ph[i].offset+j];}
 boundary(0x804ab74,reinterpret_cast<unsigned>(&probe_allocate));boundary(0x804c070,reinterpret_cast<unsigned>(&probe_status));
 *reinterpret_cast<unsigned*>(context+0x20)=1;const void* ptr=segment;*reinterpret_cast<const void***>(context+4)=&ptr;
 fd=open(argv[2],0);if(fd<0)return 20;unsigned cases;if(!receive(fd,&cases,4)||cases<1||cases>65536)return 21;
 unsigned short before;asm volatile("fnstcw %0":"=m"(before));write(1,&before,2);
 for(unsigned c=0;c<cases;c++){
  double p[7];if(!receive(fd,p,sizeof(p)))return 23;heap_used=0;
  *reinterpret_cast<double*>(segment+0xcc)=p[0];*reinterpret_cast<double*>(segment+0xd4)=p[1];*reinterpret_cast<int*>(segment+0xe0)=int(p[5]);*reinterpret_cast<int*>(segment+0xe4)=int(p[6]);
  *reinterpret_cast<double*>(0x80ce588)=p[2];*reinterpret_cast<double*>(0x80ce590)=p[3];*reinterpret_cast<int*>(0x80ce5a8)=int(p[4]);
  const int status=reinterpret_cast<unsigned char(*)(void*)>(0x8064f6c)(context)?1:0;
  const int output[]={**reinterpret_cast<int**>(context+0x18),**reinterpret_cast<int**>(context+0x1c),*reinterpret_cast<int*>(context+0x24),status,int(context[0x4a])+256*int(context[0x4b])};write(1,output,20);
 }
 unsigned short after;asm volatile("fnstcw %0":"=m"(after));write(1,&after,2);close(fd);return 0;
}
asm(".text\n.global _start\n_start:\n"
 "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
 "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
 "call __libc_start_main\nhlt\n");
