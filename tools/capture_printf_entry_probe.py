"""Independent public variadic/va_list calls through the pinned i386 libc.

Uses the same read-only full-state observer as the ASITIC cohort. A normal
native caller supplies declared string, integer and binary64 arguments;
no child, register, instruction or later return is substituted.
"""
import argparse,gzip,hashlib,json,subprocess,tempfile
from pathlib import Path
import capture_printf_entry_original as entry
from capture_printf_integer_original import LIBC_SHA256,PROBE as INTEGER_PROBE
from capture_getline_bytes_original import integer_cpu

ROOT=Path(__file__).resolve().parents[1]
VALUES=((0,0x3ff40000),(0,0x80000000),(1,0),(0xffffffff,0x7fefffff),(0,0x7ff00000),(0,0x7ff80000))


def requests():return [dict(kind=kind,string='probe',integer=0x12340000+i,double_bits=(lo.to_bytes(4,'little')+hi.to_bytes(4,'little')).hex())for i,(lo,hi)in enumerate(VALUES)for kind in('printf','fprintf','vfprintf_public')]


def source():
    rows=',\n'.join('{%su,%su}'%(lo,hi)for lo,hi in VALUES)
    return r'''
typedef struct _IO_FILE FILE;
extern FILE *stdout;
extern void *malloc(unsigned);
extern int printf(const char *, ...), fprintf(FILE *, const char *, ...);
extern int vfprintf(FILE *, const char *, __builtin_va_list);
extern int fflush(FILE *);
__attribute__((noinline)) static int via_list(FILE *file,const char *format,...) {
 __builtin_va_list args;__builtin_va_start(args,format);
 int count=vfprintf(file,format,args);__builtin_va_end(args);return count;
}
int main(void) {
 void *volatile earlier=malloc(32);if(!earlier)return 2;
 const unsigned bits[][2]={'''+rows+r'''};
 for(unsigned i=0;i<sizeof(bits)/sizeof(bits[0]);i++) {
  union {unsigned words[2];double value;} v={{bits[i][0],bits[i][1]}};
  const char *format="P:%s:%08x:% .3g:S";
  if(printf(format,"probe",0x12340000u+i,v.value)<0)return 3;
  if(fprintf(stdout,format,"probe",0x12340000u+i,v.value)<0)return 4;
  if(via_list(stdout,format,"probe",0x12340000u+i,v.value)<0)return 5;
 }
 return fflush(stdout)!=0;
}
'''+INTEGER_PROBE[INTEGER_PROBE.index('__asm__('):]


OBSERVER=entry.replace_once(entry.OBSERVER,"for pc in (0x8050b2c,0x8051280):FileDriver('*'+hex(pc),internal=True)",
    "class ProbeMain(gdb.Breakpoint):\n def stop(self):return FileDriverReturn.stop(self)\nProbeMain('main',internal=True)")
OBSERVER=entry.replace_once(OBSERVER,"for off,kind in ((0x586c0,'init')", "for off,kind in ((0x17fb00,'old-xsputn'),(0x84fb0,'overflow-dispatch'),(0x7dd10,'file-orientation'),(0x17f350,'old-overflow'),(0x17efe0,'old-do-write'),(0x586c0,'init')")


def commands(directory):return entry.commands(directory).replace(entry.OBSERVER,OBSERVER).replace('run -g -t process.tek -x input.asit < answers.txt','run')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cc',default='cc');p.add_argument('--debug-directory',type=Path,required=True);p.add_argument('--libc',type=Path,default=Path('/lib/i386-linux-gnu/libc.so.6'));p.add_argument('--output',type=Path,default=ROOT/'tests/fixtures/printf_entry_probe.json.gz');args=p.parse_args();libc=args.libc.resolve()
    if hashlib.sha256(libc.read_bytes()).hexdigest()!=LIBC_SHA256:raise ValueError('Probe libc differs from the pinned original')
    program=source();gdb_commands=commands(args.debug_directory);env=entry.parent.lifetime.native_environment(str(libc.parent));projection=entry.parent.parent.Projection();cpu=integer_cpu(args.cc)
    with tempfile.TemporaryDirectory(prefix='pyasitic-printf-entry-probe-')as directory:
        d=Path(directory);binary=d/'probe';(d/'probe.c').write_text(program);(d/'capture.gdb').write_text(gdb_commands)
        command=[args.cc,'-m32','-O2','-std=c11','-fno-builtin','-fno-pie','-no-pie','-nostdlib',str(d/'probe.c'),str(libc),'-Wl,-e,_start','-Wl,--dynamic-linker=/lib/i386-linux-gnu/ld-linux.so.2','-o',str(binary)]
        built=subprocess.run(command,capture_output=True,text=True,check=True)
        plain=subprocess.run([str(binary)],cwd=d,env=env,capture_output=True,check=True,start_new_session=True,timeout=60)
        native=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(binary)],cwd=d,env=env,capture_output=True,text=True,check=True,start_new_session=True,timeout=180)
        if 'Python Exception'in native.stderr:raise ValueError(native.stderr)
        case=dict(label='independent-public-entry',cache_mode='native',**json.loads((d/'heap.json').read_text()))
        if case['signal']or case['native_exit']!=0 or len(case['printf_calls'])!=len(requests()):raise ValueError('Incomplete public entry native probe')
        projection.case(case)
        record=dict(libc_sha256=LIBC_SHA256,source=program,source_sha256=hashlib.sha256(program.encode()).hexdigest(),requests=requests(),compile_command=command,compile_stderr=built.stderr,executable_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),gdb_commands=gdb_commands,observer=OBSERVER,environment=env,integer_cpu=cpu,plain=dict(returncode=plain.returncode,stdout=plain.stdout.hex(),stderr=plain.stderr.hex()),native=dict(stdout=native.stdout,stderr=native.stderr),cases=[case],**projection.metadata())
    with gzip.GzipFile(str(args.output),'wb',mtime=0)as stream:stream.write((json.dumps(record,separators=(',',':'))+'\n').encode())
    print(len(requests()),'independent full-state public entry calls',args.output)


if __name__=='__main__':main()
