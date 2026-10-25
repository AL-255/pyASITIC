"""Independent int32 format requests evaluated by the pinned original libc."""
import argparse,gzip,hashlib,json,os,struct,subprocess,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LIBC_SHA256='e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0'
PROBE=r'''
typedef unsigned int u32;
typedef struct _IO_FILE FILE;
extern FILE *stdin, *stdout;
extern char *fgets(char *, int, FILE *);
extern unsigned long strtoul(const char *, char **, int);
extern int snprintf(char *, unsigned int, const char *, ...);
extern unsigned int fwrite(const void *, unsigned int, unsigned int, FILE *);
int main(void) {
 char line[256], result[128];
 while (fgets(line, sizeof line, stdin)) {
  char *tab=line; while (*tab && *tab!='\t') ++tab;
  if (*tab!='\t') return 2;
  *tab++=0; u32 value=strtoul(tab, (void *)0, 16);
  char *conversion=line; int is_long=0;
  while (*conversion && *conversion!='%') ++conversion;
  while (*conversion && *conversion!='d' && *conversion!='i' && *conversion!='u'
         && *conversion!='o' && *conversion!='x' && *conversion!='X') {
   if (*conversion=='l') is_long=1;
   ++conversion;
  }
  int is_signed=*conversion=='d' || *conversion=='i'; int count;
  if (is_long) {
   if (is_signed) count=snprintf(result, sizeof result, line, (long)(int)value);
   else count=snprintf(result, sizeof result, line, (unsigned long)value);
  } else {
   if (is_signed) count=snprintf(result, sizeof result, line, (int)value);
   else count=snprintf(result, sizeof result, line, value);
  }
  if (count<0 || count>=(int)sizeof result) return 3;
  if (fwrite(&count, 4, 1, stdout)!=1 || fwrite(result, 1, count, stdout)!=(u32)count) return 4;
 }
 return 0;
}
__asm__(".text\n.globl _start\n_start:\n"
 "xorl %ebp,%ebp\n popl %esi\n movl %esp,%ecx\n andl $-16,%esp\n"
 "pushl %eax\n pushl %esp\n pushl %edx\n pushl $0\n pushl $0\n"
 "pushl %ecx\n pushl %esi\n pushl $main\n call __libc_start_main@PLT\n hlt\n");
'''


def requests():
    values=(0,1,7,8,9,10,15,16,127,128,255,256,32767,32768,65535,65536,0x7fffffff,0x80000000,0xffffffff)
    specifications=(('','',''),('','3',''),('0','8',''),('-','8',''),('+','8',''),(' ','8',''),
                    ('','8','.0'),('','8','.2'),('','8','.12'),('-','8','.12'),('#','8',''),('#0','8','.0'))
    return [dict(format='P:%'+flags+width+precision+modifier+code+':S',value=value)
            for code in 'diuoxX'for modifier in ('','h','hh','l')for flags,width,precision in specifications for value in values]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cc',default='cc');p.add_argument('--libc',type=Path,default=Path('/lib/i386-linux-gnu/libc.so.6'));p.add_argument('--output',type=Path,default=ROOT/'tests/fixtures/printf_integer_original.json.gz');args=p.parse_args()
    libc=args.libc.resolve();assert hashlib.sha256(libc.read_bytes()).hexdigest()==LIBC_SHA256
    cases=requests();stdin=''.join(c['format']+'\t'+format(c['value'],'x')+'\n'for c in cases)
    env=dict(PATH=os.defpath,HOME='/tmp',LANG='C',LC_ALL='C',LD_LIBRARY_PATH=str(libc.parent))
    with tempfile.TemporaryDirectory(prefix='pyasitic-printf-int-')as directory:
        d=Path(directory);source=d/'probe.c';binary=d/'probe';source.write_text(PROBE)
        command=[args.cc,'-m32','-O2','-std=c11','-fno-pie','-no-pie','-nostdlib',str(source),str(libc),'-Wl,-e,_start','-Wl,--dynamic-linker=/lib/i386-linux-gnu/ld-linux.so.2','-o',str(binary)]
        compile_result=subprocess.run(command,capture_output=True,text=True,check=True)
        result=subprocess.run([str(binary)],input=stdin.encode(),env=env,capture_output=True,check=True,start_new_session=True)
        raw=result.stdout;offset=0
        for case in cases:
            n=struct.unpack_from('<I',raw,offset)[0];offset+=4;assert n<128 and offset+n<=len(raw)
            case['original']=raw[offset:offset+n].hex();offset+=n
        assert offset==len(raw)and not result.stderr
        record=dict(libc_sha256=LIBC_SHA256,probe=PROBE,compile_command=command,compile_stderr=compile_result.stderr,
                    probe_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),environment=env,stdin_sha256=hashlib.sha256(stdin.encode()).hexdigest(),cases=cases,
                    reference='All independent int32 cases execute the unmodified pinned i386 libc snprintf through a normal variadic call with matching integer types. The harness only records result lengths and bytes. No instruction, allocation, affinity, register or return-state substitution is used. These text-output probes supplement, and do not replace or filter, the complete original ASITIC formatter-state gates.')
    with gzip.GzipFile(str(args.output),'wb',mtime=0)as stream:stream.write((json.dumps(record,separators=(',',':'))+'\n').encode())
    print(len(cases),'independent native int32 formats',args.output)


if __name__=='__main__':main()
