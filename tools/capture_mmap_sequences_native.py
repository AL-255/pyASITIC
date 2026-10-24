"""Independent i386 libc histories for mmap reuse and dynamic thresholds.

These are libc probes, not original-ASITIC numerical outputs. The same native
allocator and read-only snapshot observer used for ASITIC are retained.
"""
import argparse,gzip,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from capture_mapping_allocator_original import OBSERVER
from capture_allocator_original import BUILD_ID
ROOT=Path(__file__).resolve().parents[1]


def jobs():
    def alloc(slot,size):return dict(kind='allocate',slot=slot,request=size)
    def free(slot):return dict(kind='free',slot=slot)
    return [
        dict(label='repeat-after-threshold-rise',operations=[alloc(0,150000),free(0),alloc(0,150000),free(0),alloc(0,150000),free(0)]),
        dict(label='middle-hole-reuse',operations=[alloc(0,700000),alloc(1,900000),alloc(2,1100000),free(1),alloc(3,800000),alloc(4,150000),free(0),free(2),free(3),free(4),alloc(0,900000),free(0)]),
        dict(label='threshold-cap',operations=[alloc(0,520000),free(0),alloc(1,524288),free(1),alloc(2,520000),free(2),alloc(3,524288),free(3)]),
        dict(label='reverse-freed-neighbours',operations=[alloc(i,size)for i,size in enumerate((150000,220000,340000,640000))]+[free(i)for i in (3,2,1,0)]+[alloc(0,340000),alloc(1,640000),free(0),free(1)]),
        dict(label='large-page-sized-blocks',operations=[alloc(0,2097152),alloc(1,2359296),free(0),alloc(2,2100000),free(1),free(2),alloc(3,4194304),free(3)]),
        dict(label='arena-and-mmap-interleaved',operations=[alloc(0,1000),alloc(1,600000),alloc(2,2000),alloc(3,700000),free(1),free(0),alloc(4,550000),free(2),alloc(5,1016),free(3),free(4),free(5)]),
    ]


START=r'''.text
.globl _start
_start:
 xorl %ebp,%ebp
 popl %esi
 movl %esp,%ecx
 andl $-16,%esp
 pushl %eax
 pushl %esp
 pushl %edx
 pushl $0
 pushl $0
 pushl %ecx
 pushl %esi
 pushl $main
 call __libc_start_main@PLT
 hlt
.section .note.GNU-stack,"",@progbits
'''


def source():
    rows=[];lengths=[]
    for job in jobs():
        operations=job['operations'];lengths.append(str(len(operations)))
        rows.append('{'+','.join('{%d,%d,%d}'%(op['kind']=='allocate',op['slot'],op.get('request',0))for op in operations)+'}')
    return r'''
extern void *malloc(unsigned);
extern void free(void *);
struct op {int kind,slot; unsigned request;};
static const struct op operations[][32]={'''+','.join(rows)+r'''};
static const unsigned lengths[]={'''+','.join(lengths)+r'''};
void *pointers[32];
__attribute__((noinline)) void checkpoint(int kind,int slot,unsigned request,void *address) {__asm__ volatile ("" ::: "memory");}
int main(int argc,char **argv) {
 unsigned scenario=0; if(argc>1)for(char *p=argv[1];*p;++p)scenario=scenario*10+*p-'0';
 if(scenario>=sizeof(lengths)/sizeof(lengths[0]))return 2;
 void *warm=malloc(16);free(warm);checkpoint(-1,0,0,0);
 for(unsigned i=0;i<lengths[scenario];++i) {
  struct op op=operations[scenario][i];void *address;
  if(op.kind){address=malloc(op.request);if(!address)return 3;pointers[op.slot]=address;}
  else {address=pointers[op.slot];free(address);pointers[op.slot]=0;}
  checkpoint(op.kind,op.slot,op.request,address);
 }
 return 0;
}
'''


def commands(debug_directory,ordinal):
    return '''set debug-file-directory %s
set debuginfod enabled off
set disable-randomization on
set pagination off
set confirm off
python
import gdb,struct,json
events=[]
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def u32(a):return struct.unpack('<I',mem(a,4))[0]
def reg(k):return int(gdb.parse_and_eval('$'+k))&0xffffffff
'''%debug_directory+OBSERVER+'''
class Checkpoint(gdb.Breakpoint):
 def stop(self):
  # Stop at the entry instruction so arguments still follow the i386 ABI.
  esp=reg('esp');kind=u32(esp+4);slot=u32(esp+8);request=u32(esp+12);address=u32(esp+16)
  if kind==0xffffffff:allocator_snapshot('scope')
  else:
   events.append(dict(kind='allocate'if kind else'free',slot=slot,request=request,address=address))
   allocator_snapshot('operation.%d'%(len(events)-1))
  return False
Checkpoint('*checkpoint',internal=True)
end
run __ORDINAL__
python
open('observations.json','w').write(json.dumps(dict(events=events,states=allocator_states,exit_code=int(gdb.parse_and_eval('$_exitcode')))))
end
quit
'''.replace('__ORDINAL__',str(ordinal))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--debug-directory',type=Path,required=True);parser.add_argument('--libc',type=Path,default=Path('/lib/i386-linux-gnu/libc.so.6'));options=parser.parse_args()
    notes=subprocess.run(['readelf','-n',str(options.libc)],capture_output=True,text=True,check=True).stdout
    assert 'Build ID: '+BUILD_ID in notes
    debug=options.debug_directory/'.build-id'/BUILD_ID[:2]/(BUILD_ID[2:]+'.debug')
    notes=subprocess.run(['readelf','-n',str(debug)],capture_output=True,text=True,check=True).stdout
    assert 'Build ID: '+BUILD_ID in notes
    cases=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-native-mapping-sequences-')as directory:
        work=Path(directory);(work/'start.s').write_text(START);(work/'probe.c').write_text(source())
        compile_commands=[['as','--32','start.s','-o','start.o'],['gcc','-m32','-O0','-g','-fno-pie','-fno-stack-protector','-fno-builtin','-c','probe.c','-o','probe.o'],['ld','-m','elf_i386','-dynamic-linker','/lib/ld-linux.so.2','start.o','probe.o',str(options.libc),'-o','probe']]
        for command in compile_commands:subprocess.run(command,cwd=work,check=True,capture_output=True)
        binary_hash=hashlib.sha256((work/'probe').read_bytes()).hexdigest()
        for ordinal,job in enumerate(jobs()):
            plain=subprocess.run([str(work/'probe'),str(ordinal)],cwd=work,capture_output=True,text=True,start_new_session=True,timeout=30)
            text=commands(options.debug_directory,ordinal);(work/'capture.gdb').write_text(text)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(work/'probe')],cwd=work,capture_output=True,text=True,start_new_session=True,timeout=60)
            if run.returncode or 'Python Exception'in run.stderr:raise RuntimeError(run.stdout[-1000:]+run.stderr[-1500:])
            observed=json.loads((work/'observations.json').read_text())
            cases.append(dict(job,commands=text,plain=dict(returncode=plain.returncode,stdout=plain.stdout,stderr=plain.stderr),stdout=run.stdout,stderr=run.stderr,**observed))
            print(job['label'],len(observed['events']),flush=True)
    versions={name:subprocess.run([name,'--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]for name in ('gcc','as','ld','gdb')}
    fixture=dict(libc_build_id=BUILD_ID,libc_sha256=hashlib.sha256(options.libc.read_bytes()).hexdigest(),debug_sha256=hashlib.sha256(debug.read_bytes()).hexdigest(),loader_sha256=hashlib.sha256(Path('/lib/ld-linux.so.2').read_bytes()).hexdigest(),source=source(),startup_source=START,binary_sha256=binary_hash,compile_commands=compile_commands,tool_versions=versions,observer=OBSERVER,reference='Independent i386 glibc histories, not original ASITIC simulation outputs. Read-only GDB observer; no inferior calls or memory/register modifications.',cases=cases)
    with gzip.GzipFile(str(ROOT/'tests/fixtures/mmap_sequences_native.json.gz'),'wb',mtime=0)as stream:stream.write((json.dumps(fixture,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
