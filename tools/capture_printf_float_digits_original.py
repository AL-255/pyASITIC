"""Independent binary64 decimal requests to the pinned, unmodified i386 libc."""
import argparse,gzip,hashlib,json,os,random,struct,subprocess,tempfile
from pathlib import Path
from capture_printf_integer_original import LIBC_SHA256

ROOT=Path(__file__).resolve().parents[1]
PROBE=r'''
typedef unsigned int u32;
typedef struct _IO_FILE FILE;
extern FILE *stdin, *stdout;
extern char *fgets(char *, int, FILE *);
extern unsigned long strtoul(const char *, char **, int);
extern int snprintf(char *, unsigned int, const char *, ...);
extern unsigned int fwrite(const void *, unsigned int, unsigned int, FILE *);
extern int fesetround(int);
struct dl_info { const char *name; void *base; const char *symbol; void *address; };
extern int dladdr(const void *, struct dl_info *);
extern void *dlsym(void *, const char *);
int main(void) {
 struct dl_info image;
 if (!dladdr(dlsym((void *)0, "snprintf"), &image)) return 6;
 typedef int (*extract_fn)(u32 *, int, int *, int *, double);
 extract_fn extract=(extract_fn)((char *)image.base+0x51ed0);
 u32 zero_count;
 __asm__ volatile ("tzcnt %1,%0" : "=r"(zero_count) : "r"(0U) : "cc");
 if (fwrite(&zero_count, 4, 1, stdout)!=1) return 7;
 char line[256], result[8192];
 while (fgets(line, sizeof line, stdin)) {
  char *tab=line; while (*tab && *tab!='\t') ++tab;
  if (*tab!='\t') return 2;
  *tab++=0;
  union { double d; u32 word[2]; } value;
  value.word[1]=strtoul(tab, &tab, 16);
  value.word[0]=strtoul(tab, &tab, 16);
  u32 mode=strtoul(tab, (void *)0, 10);
  if (mode>3 || fesetround((int)(mode<<10))) return 3;
  struct { int count, exponent, negative; u32 limbs[4]; } extracted;
  extracted.count=extracted.exponent=extracted.negative=-1;
  for (int i=0; i<4; ++i) extracted.limbs[i]=0xa5a5a5a5U;
  if ((value.word[1]&0x7ff00000U)!=0x7ff00000U)
   extracted.count=extract(extracted.limbs, 4, &extracted.exponent, &extracted.negative, value.d);
  int count=snprintf(result, sizeof result, line, value.d);
  if (count<0 || count>=(int)sizeof result) return 4;
  if (fwrite(&count, 4, 1, stdout)!=1 || fwrite(result, 1, count, stdout)!=(u32)count) return 5;
  if (fwrite(&extracted, sizeof extracted, 1, stdout)!=1) return 8;
 }
 return 0;
}
__asm__(".text\n.globl _start\n_start:\n"
 "xorl %ebp,%ebp\n popl %esi\n movl %esp,%ecx\n andl $-16,%esp\n"
 "pushl %eax\n pushl %esp\n pushl %edx\n pushl $0\n pushl $0\n"
 "pushl %ecx\n pushl %esi\n pushl $main\n call __libc_start_main@PLT\n hlt\n");
'''


def requests():
    """Declared inputs: boundaries, every exponent, and seeded bit patterns.

    No native result selects, filters, or initializes any request. Adjacent
    representable values test carry/tie decisions without decimal parsing.
    """
    values={0,1,2,(1<<52)-1,1<<52,(1<<52)+1,0x7fefffffffffffff,
            0x7ff0000000000000,0x7ff0000000000001,0x7ff8000000000000,0x7fffffffffffffff}
    for value in(.00001,.0001,.001,.01,.1,.5,1.,1.25,2.5,7.5,8.,9.5,9.95,9.99,10.,99.9,100.,999.5,1000.,1e6,1e20):
        word=struct.unpack('<Q',struct.pack('<d',value))[0]
        values.update((word-1,word,word+1))
    values=sorted(values|{v|(1<<63)for v in values})
    fields=(('',0,-1),('',0,0),('',0,1),('',0,2),('',0,6),('',0,17),('',0,25),
            ('#',0,0),('#',0,2),('0+',20,6),('-#',24,17),(' ',18,2),('0',5,0),('-+0',12,2),(' #+',24,0),('#',20,4))
    cases=[]
    def add(word,spec,flags='',width=0,precision=-1,rounding=0,modifier=''):
        fmt='P:%'+flags+(str(width)if width else'')+('.'+str(precision)if precision>=0 else'')+modifier+spec+':S'
        cases.append(dict(format=fmt,word=word,spec=spec,flags=flags,width=width,precision=precision,rounding=rounding))
    for mode in range(4):
        for spec in'eEfFgG':
            for flags,width,precision in fields:
                for word in values:add(word,spec,flags,width,precision,mode,'l'if len(cases)&1 else'')
    # All biased exponents, including zero/subnormal and infinity/NaN. Three
    # significands and both signs exercise the entire binary64 exponent range.
    for exponent in range(2048):
        for mantissa in(0,1,(1<<52)-1):
            for sign in range(2):
                i=len(cases);add((sign<<63)|(exponent<<52)|mantissa,'eEfFgG'[i%6],precision=(0,1,6,17,25)[exponent%5],rounding=(exponent+sign)%4)
    rng=random.Random(0x415349544943)
    for i in range(4096):
        flags,width,precision=fields[i%len(fields)];add(rng.getrandbits(64),'eEfFgG'[i%6],flags,width,precision,i%4)
    for word in(1,(1<<52)-1,1<<52,0x3fefffffffffffff,0x7fefffffffffffff):
        for spec in'eEfFgG':
            for mode in range(4):add(word,spec,'#',0,1074,mode)
    for spec in'eEfFgG':
        for mode in range(4):add(0x3ff4000000000000,spec,'0+',4096,2,mode)
    return cases


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cc',default='cc');p.add_argument('--libc',type=Path,default=Path('/lib/i386-linux-gnu/libc.so.6'));p.add_argument('--libm',type=Path,default=Path('/lib/i386-linux-gnu/libm.so.6'));p.add_argument('--output',type=Path,default=ROOT/'tests/fixtures/printf_float_digits_original.json.gz');args=p.parse_args()
    libc=args.libc.resolve();libm=args.libm.resolve();assert hashlib.sha256(libc.read_bytes()).hexdigest()==LIBC_SHA256
    cases=requests();stdin=''.join(c['format']+'\t'+format(c['word']>>32,'x')+' '+format(c['word']&0xffffffff,'x')+' '+str(c['rounding'])+'\n'for c in cases)
    env=dict(PATH=os.defpath,HOME='/tmp',LANG='C',LC_ALL='C',LD_LIBRARY_PATH=str(libc.parent))
    with tempfile.TemporaryDirectory(prefix='pyasitic-printf-float-')as directory:
        d=Path(directory);source=d/'probe.c';binary=d/'probe';source.write_text(PROBE)
        command=[args.cc,'-m32','-O2','-std=c11','-fno-pie','-no-pie','-nostdlib',str(source),str(libm),str(libc),'-Wl,-e,_start','-Wl,--dynamic-linker=/lib/i386-linux-gnu/ld-linux.so.2','-o',str(binary)]
        compile_result=subprocess.run(command,capture_output=True,text=True,check=True)
        result=subprocess.run([str(binary)],input=stdin.encode(),env=env,capture_output=True,check=True,start_new_session=True)
        raw=result.stdout;zero_count=struct.unpack_from('<I',raw)[0];offset=4
        assert zero_count==32, 'This decimal source requires the captured TZCNT zero result'
        for case in cases:
            n=struct.unpack_from('<I',raw,offset)[0];offset+=4;assert n<8192 and offset+n<=len(raw)
            case['original']=raw[offset:offset+n].hex();offset+=n
            count,exponent,negative,*words=struct.unpack_from('<iii4I',raw,offset);offset+=28
            case['extraction']=dict(count=count,exponent=exponent,negative=negative,limbs=words)if count!=-1 else None
        assert offset==len(raw)and not result.stderr
        record=dict(libc_sha256=LIBC_SHA256,libm_sha256=hashlib.sha256(libm.read_bytes()).hexdigest(),probe=PROBE,compile_command=command,compile_stderr=compile_result.stderr,
                    probe_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),environment=env,stdin_sha256=hashlib.sha256(stdin.encode()).hexdigest(),tzcnt_zero=zero_count,extract_double_offset=0x51ed0,cases=cases,
                    reference='Independent binary64 decimal requests through normal variadic snprintf calls in the unmodified pinned i386 libc, plus normal typed calls to its __mpn_extract_double at the pinned ELF offset resolved from the loaded libc base by dladdr. The standalone probe uses fesetround to request each of the four earlier rounding modes and records its native TZCNT zero result, finite mantissa extraction, lengths and output bytes. This does not alter ASITIC or its CPU controls, fit values, replace native instructions or return states, or replace/filter any full original formatter-state target.')
    with gzip.GzipFile(str(args.output),'wb',mtime=0)as stream:stream.write((json.dumps(record,separators=(',',':'))+'\n').encode())
    print(len(cases),'independent native binary64 decimal formats',args.output)


if __name__=='__main__':main()
