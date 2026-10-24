"""Native x87 trig outputs, with independent cases and original-command anchors."""
import argparse,gzip,hashlib,json,math,random,struct,subprocess,tempfile
from pathlib import Path
from capture_log_instructions_native import SOURCE as LOG_SOURCE,double,raw
ROOT=Path(__file__).resolve().parents[1]
SOURCE=LOG_SOURCE.replace('fldt %2;fldt %1;fyl2x;fstpt %0','fldt %1;fcos;fstpt %0').replace('fldt %2;fldt %1;fyl2xp1;fstpt %0','fldt %1;fsin;fstpt %0')


def independent_cases():
    rng=random.Random(0x54524947)
    def both(label,word):
        for mode in(0,1):yield dict(label=label,operation=mode,input_words=[word])
    for i in range(2048):yield from both('ordinary-binary64',double(rng.uniform(-4,4)))
    for i in range(1024):yield from both('ordinary-extended',raw(rng.randrange(1<<63,1<<64),0x3fff+rng.randrange(-5,3),bool(i&1)))
    # Independent reduced-angle, table and quadrant boundaries. All neighbors
    # are chosen before examining their returned words.
    for numerator in range(-16,17):
        base=numerator*math.pi/8
        sig,exp=struct.unpack('<QH',bytes.fromhex(double(base)))
        if not base:
            for value in(0.,-0.,2.**-70,-2.**-70):yield from both('zero',double(value))
            continue
        for delta in range(-16,17):
            if 1<<63<=sig+delta<1<<64:yield from both('extended-angle-neighbors',raw(sig+delta,exp&0x7fff,bool(exp&0x8000)))
        for direction in(-math.inf,math.inf):
            value=base
            for step in range(16):
                value=math.nextafter(value,direction);yield from both('binary64-angle-neighbors',double(value))
    for i in range(512):yield from both('tiny-extended',raw(rng.randrange(1<<63,1<<64),0x3fff-rng.randrange(5,128),bool(i&1)))
    for exponent in(4,16,32,48,62):
        for i in range(32):yield from both('wide-argument',raw(rng.randrange(1<<63,1<<64),0x3fff+exponent,bool(i&1)))
    for value in(2.**63,-2.**63,2.**64,-2.**64):yield from both('out-of-range',double(value))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--libc',type=Path,default=Path('/lib/i386-linux-gnu/libc.so.6'));p.add_argument('--loader',type=Path,default=Path('/lib/ld-linux.so.2'));a=p.parse_args()
    rows=list(independent_cases());parents={}
    for name in('mutual_command_traces_original.json','coupling_command_traces_original.json','join_mutual_traces_original.json.gz'):
        path=ROOT/'tests/fixtures'/name;parents[name]=hashlib.sha256(path.read_bytes()).hexdigest();data=gzip.decompress(path.read_bytes())if name.endswith('.gz')else path.read_bytes()
        for ci,c in enumerate(json.loads(data)['cases']):
            for ei,e in enumerate(c['events']):
                for mi,op in enumerate(e.get('math',[])):
                    if op['operation']in('fcos','fsin'):
                        rows.append(dict(label='actual-original-command',operation=int(op['operation']=='fsin'),input_words=op['input_words'],original_output_words=op['output_words'],parent=[name,ci,ei,mi]))
    flags=['-m32','-O2','-mfpmath=sse','-msse2','-fno-pie','-fno-pic','-fno-stack-protector','-fno-exceptions','-fno-rtti','-nostdlib','-no-pie']
    with tempfile.TemporaryDirectory(prefix='pyasitic-native-trig-')as directory:
        d=Path(directory);(d/'probe.cpp').write_text(SOURCE);payload=d/'input.bin'
        payload.write_bytes(struct.pack('<I',len(rows))+b''.join(struct.pack('<I',r['operation'])+bytes.fromhex(r['input_words'][0])+bytes(10)for r in rows))
        subprocess.run(['g++',*flags,str(d/'probe.cpp'),str(a.libc),'-Wl,--dynamic-linker='+str(a.loader),'-o',str(d/'probe')],check=True)
        run=subprocess.run([str(d/'probe'),str(payload)],capture_output=True,start_new_session=True,timeout=60)
    if run.returncode or len(run.stdout)!=4+10*len(rows):raise RuntimeError('Native trig capture failed: '+repr((run.returncode,run.stderr)))
    before=struct.unpack_from('<H',run.stdout)[0];after=struct.unpack_from('<H',run.stdout,len(run.stdout)-2)[0];assert before==after==0x37f
    anchors=0
    for i,c in enumerate(rows):
        c['output_words']=run.stdout[2+10*i:12+10*i].hex()
        if 'original_output_words'in c:assert c['original_output_words']==c['output_words'],c;anchors+=1
    cpu={}
    for line in Path('/proc/cpuinfo').read_text().split('\n\n',1)[0].splitlines():
        if ':'in line:
            k,v=map(str.strip,line.split(':',1))
            if k in('vendor_id','model name','cpu family','model','stepping','microcode'):cpu[k]=v
    result=dict(reference='Native i386 FCOS/FSIN driver. This is not the ASITIC executable. Fixed-seed independent inputs and separately identified unchanged-original operands; no replacements or patched results.',source=SOURCE,source_sha256=hashlib.sha256(SOURCE.encode()).hexdigest(),compile_flags=flags,compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],libc_sha256=hashlib.sha256(a.libc.resolve().read_bytes()).hexdigest(),loader_sha256=hashlib.sha256(a.loader.resolve().read_bytes()).hexdigest(),cpu=cpu,control_before=before,control_after=after,parents=parents,original_anchor_count=anchors,cases=rows)
    output=ROOT/'tests/fixtures/trig_instructions_native.json.gz'
    with gzip.GzipFile(str(output),'wb',mtime=0)as stream:stream.write((json.dumps(result,separators=(',',':'))+'\n').encode())
    print(len(rows),'native trig outputs;',anchors,'unchanged-original words matched.')


if __name__=='__main__':main()
