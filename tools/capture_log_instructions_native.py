"""Capture native x87 logarithm words; label instruction and ASITIC references separately."""
import argparse,gzip,hashlib,json,math,random,struct,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=r'''
extern "C" int open(const char*,int,...),read(int,void*,unsigned),write(int,const void*,unsigned),close(int);
struct __attribute__((packed)) Extended { unsigned long long significand;unsigned short exponent; };
extern "C" int probe_main(int,char** argv){
 int fd=open(argv[1],0);if(fd<0)return 1;unsigned count;if(read(fd,&count,4)!=4)return 2;
 unsigned short before,after;asm volatile("fninit;fnstcw %0":"=m"(before));write(1,&before,2);
 for(unsigned i=0;i<count;i++){
  unsigned mode;Extended in[2],out;
  if(read(fd,&mode,4)!=4||read(fd,in,20)!=20)return 3;
  if(mode==0)asm volatile("fldt %2;fldt %1;fyl2x;fstpt %0":"=m"(out):"m"(in[0]),"m"(in[1]):"st");
  else asm volatile("fldt %2;fldt %1;fyl2xp1;fstpt %0":"=m"(out):"m"(in[0]),"m"(in[1]):"st");
  write(1,&out,10);
 }
 asm volatile("fnstcw %0":"=m"(after));write(1,&after,2);close(fd);return 0;
}
asm(".text\n.global _start\n_start:\nxorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\npushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\ncall __libc_start_main\nhlt\n");
'''

def raw(sig,exponent,negative=False):return struct.pack('<QH',sig,exponent|int(negative)<<15).hex()
def double(value):
 mantissa,exponent=math.frexp(value)
 return raw(int(abs(mantissa)*(1<<64)),16383+exponent-1 if value else 0,math.copysign(1.,value)<0)

def independent_cases():
 rng=random.Random(0x4c4f4732);ln2=raw(0xb17217f7d1cf79ac,0x3ffe);one=raw(1<<63,0x3fff)
 def row(label,x,y=ln2,mode=0):return dict(label=label,operation=mode,input_words=[x,y])
 for exponent in (1,0x3f00,0x3ffe,0x3fff,0x4000,0x40ff,0x7ffe):
  for top in range(32):
   boundary=(1<<63)|(top<<58)
   for offset in(-1,0,1,(1<<57)-1,1<<57,(1<<57)+1):
    sig=boundary+offset
    if (1<<63)<=sig<(1<<64):yield row('table-boundary',raw(sig,exponent))
 for i in range(2048):
  yield row('wide-exponent',raw(rng.randrange(1<<63,1<<64),rng.randrange(1,0x7fff)),one if i%3==0 else ln2)
 for i in range(2048):yield row('ordinary-exponent',raw(rng.randrange(1<<63,1<<64),0x3fff+rng.randrange(-128,129)))
 for exponent,sig in ((0x3ffe,0xe000000000000000),(0x3fff,0x9000000000000000),(0x3fff,1<<63)):
  for delta in range(-16,17):
   e=exponent;s=sig+delta
   if s<1<<63:e-=1;s<<=1
   yield row('near-one-crossover',raw(s,e))
 for sig in (1,2,(1<<62)-1,1<<62,(1<<63)-1):yield row('extended-subnormal',raw(sig,0))
 for x in(0.,-0.,.125,-.125,2.**-70,-2.**-70,2.**-71,-2.**-71):yield row('log1p-boundary',double(x),mode=1)
 for sig in(1,2,(1<<62)-1,1<<62,(1<<63)-1):
  for neg in(False,True):yield row('log1p-subnormal',raw(sig,0,neg),mode=1)
 for i in range(2048):yield row('log1p-domain',double(rng.uniform(-.29,.41)),mode=1)
 for i in range(512):yield row('log1p-tiny',raw(rng.randrange(1<<63,1<<64),0x3fff-rng.randrange(4,16383),bool(i&1)),mode=1)


def multiplier_cases():
 # First three arguments are the differing unchanged-original instructions;
 # the remaining seven are independent ordinary arguments. All outputs come
 # from the new instruction driver, never from a correction table.
 rng=random.Random(0x80f1)
 arguments=[(0,'807a37162a4bdf8beb3f'),(0,'4d05b5b6af07de850040'),(1,'126ef571c7ced6e3fbbf')]
 arguments +=[(op,double(x))for op,x in[(0,1.03125),(0,1.1),(0,.91),(0,5.3),(1,.01),(1,-.15),(1,.3)]]
 multipliers=[raw(1<<63,0x3fff),raw(0xb17217f7d1cf79ac,0x3ffe)]
 multipliers +=[raw(rng.randrange(1<<63,1<<64),0x3fff)for _ in range(1024)]
 for group,(op,x)in enumerate(arguments):
  for y in multipliers:yield dict(label='multiplier-group',group=group,operation=op,input_words=[x,y])


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--suite',choices=('logarithms','multipliers'),default='logarithms');p.add_argument('--libc',type=Path,default=Path('/lib/i386-linux-gnu/libc.so.6'));p.add_argument('--loader',type=Path,default=Path('/lib/ld-linux.so.2'));a=p.parse_args()
 rows=list(independent_cases()if a.suite=='logarithms'else multiplier_cases());parents={}
 for name in ('mutual_command_traces_original.json','coupling_command_traces_original.json'):
  path=ROOT/'tests/fixtures'/name;parents[name]=hashlib.sha256(path.read_bytes()).hexdigest()
  for ci,c in enumerate(json.loads(path.read_text())['cases']):
   for ei,e in enumerate(c['events']):
    for mi,op in enumerate(e.get('math',[])):
     if op['operation']in('fyl2x','fyl2xp1'):
      rows.append(dict(label='actual-original-command',operation=int(op['operation']=='fyl2xp1'),input_words=op['input_words'],original_output_words=op['output_words'],parent=[name,ci,ei,mi]))
 flags=['-m32','-O2','-mfpmath=sse','-msse2','-fno-pie','-fno-pic','-fno-stack-protector','-fno-exceptions','-fno-rtti','-nostdlib','-no-pie']
 with tempfile.TemporaryDirectory(prefix='pyasitic-native-log-')as directory:
  d=Path(directory);(d/'probe.cpp').write_text(SOURCE);payload=d/'input.bin';payload.write_bytes(struct.pack('<I',len(rows))+b''.join(struct.pack('<I',r['operation'])+b''.join(bytes.fromhex(w)for w in r['input_words'])for r in rows))
  subprocess.run(['g++',*flags,str(d/'probe.cpp'),str(a.libc),'-Wl,--dynamic-linker='+str(a.loader),'-o',str(d/'probe')],check=True)
  r=subprocess.run([str(d/'probe'),str(payload)],capture_output=True,start_new_session=True,timeout=60)
 if r.returncode or len(r.stdout)!=4+10*len(rows):raise RuntimeError('Native instruction capture failed: '+repr((r.returncode,r.stderr)))
 before=struct.unpack_from('<H',r.stdout)[0];after=struct.unpack_from('<H',r.stdout,len(r.stdout)-2)[0];assert before==after==0x37f
 for i,c in enumerate(rows):
  c['output_words']=r.stdout[2+10*i:12+10*i].hex()
  if 'original_output_words'in c:assert c['original_output_words']==c['output_words'],c
 cpu={}
 for line in Path('/proc/cpuinfo').read_text().split('\n\n',1)[0].splitlines():
  if ':'in line:
   k,v=map(str.strip,line.split(':',1))
   if k in('vendor_id','model name','cpu family','model','stepping','microcode'):cpu[k]=v
 result=dict(suite=a.suite,reference='Native i386 FYL2X/FYL2XP1 instruction driver; Independent fixed-seed logarithm inputs or explicitly selected multiplier groups, plus 67 separately identified unchanged-original command operands. This driver is not the ASITIC executable. No operands or returned words are patched.',source=SOURCE,source_sha256=hashlib.sha256(SOURCE.encode()).hexdigest(),compile_flags=flags,compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],libc_sha256=hashlib.sha256(a.libc.resolve().read_bytes()).hexdigest(),loader_sha256=hashlib.sha256(a.loader.resolve().read_bytes()).hexdigest(),cpu=cpu,control_before=before,control_after=after,parents=parents,cases=rows)
 out=ROOT/'tests/fixtures'/('log_instructions_native.json.gz'if a.suite=='logarithms'else'log_multipliers_native.json.gz')
 with gzip.GzipFile(str(out),'wb',mtime=0)as stream:stream.write((json.dumps(result,separators=(',',':'))+'\n').encode())
 print(len(rows),'native logarithm instruction outputs captured; all 67 actual-original command words matched.')
if __name__=='__main__':main()
