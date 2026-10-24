"""Capture unchanged-original TRANS/BALUN descriptors and both completed windings."""
import argparse,hashlib,json,math,os,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]
COMMANDS=r'''
set pagination off
set confirm off
set environment TERM dumb
set environment INPUTRC /dev/null
break *ENTRY
run -g -t process.tek -x input.asit < answers.txt
python
import gdb,struct,json
def memory(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def u32(a):return struct.unpack('<I',memory(a,4))[0]
def i32(a):return struct.unpack('<i',memory(a,4))[0]
def f64(a):return struct.unpack('<d',memory(a,8))[0]
def name(a):return memory(a,80).split(b'\0')[0].decode('latin1')
def config(a):return dict(name=name(a),length=f64(a+0x70),height=f64(a+0x78),width=f64(a+0x88),spacing=f64(a+0x90),turns=f64(a+0x98),angle=f64(a+0xa0),metal=i32(a+0x68),exit_metal=i32(a+0x6c),phase=i32(a+0xac),x=f64(a+0x54),y=f64(a+0x5c))
control_before=int(gdb.parse_and_eval('$fctrl'));esp=int(gdb.parse_and_eval('$esp'));ret=u32(esp)
configs=[config(u32(esp+4))]
gdb.breakpoints()[0].enabled=False
if KIND=='transformer':configs.append(config(u32(esp+8)))
else:
 gdb.Breakpoint('*0x8059854',temporary=True,internal=True);gdb.execute('continue',to_string=True)
 esp=int(gdb.parse_and_eval('$esp'));configs.append(config(u32(esp+4)))
 gdb.Breakpoint('*0x807a8b8',temporary=True,internal=True);gdb.execute('continue',to_string=True)
 esp=int(gdb.parse_and_eval('$esp'));ret=u32(esp)
gdb.Breakpoint('*'+hex(ret),temporary=True,internal=True);gdb.execute('continue',to_string=True)
for _ in range(64):
 head=u32(0x80ce558);other=u32(head+0xb0)
 if other and u32(head+0xb4)==other and u32(other+0xb4)==head:break
 gdb.execute('stepi',to_string=True)
else:raise AssertionError('Native paired links did not complete')
metal_count=i32(0x80d8904)
def record(shape):
 out=dict(name=name(shape),origin=[f64(shape+0x54),f64(shape+0x5c)],origin_bits=memory(shape+0x54,16).hex(),segments=[])
 a=u32(shape+0xa8)
 while a:
  assert len(out['segments'])<20000
  m=i32(a+0xdc);item=dict(coordinates_bits=b''.join(memory(a+o,24)for o in(0,24,0x44,0x5c,0x88,0xa0)).hex(),width_bits=memory(a+0xcc,8).hex(),metal=m)
  if m<metal_count:item['thickness_bits']=memory(a+0xd4,8).hex()
  else:item.update(nx=i32(a+0xe0),ny=i32(a+0xe4))
  out['segments'].append(item);a=u32(a+0xec)
 return out
out=dict(configs=configs,windings=[record(other),record(head)],paired_links=True,control_before=control_before,control_after=int(gdb.parse_and_eval('$fctrl')))
open('paired.json','w').write(json.dumps(out))
end
kill
quit
'''


def jobs():
    for np,ns in [(.25,.75),(.5,1),(1.25,1),(1.75,2),(2.75,1.5)]:
        for exit in ['-1','M3']:
            for angle in [0,17,-35.5]:
                for phase in [1,-1]:
                    p=dict(name='T',primary_name='A',secondary_name='B',length=160.125,height=140.375,width=3.25,spacing=2.125,turns=np,secondary_turns=ns,metal='M4',exit_metal=exit,angle=angle,phase=phase,x=12.345,y=23.456)
                    script=f'TRANS PNAME=A:SNAME=B:LEN={p["length"]}:WID={p["height"]}:W={p["width"]}:S={p["spacing"]}:NP={np}:NS={ns}:METAL=M4:EXIT={exit}:ORIENT={angle}:PHASE={phase}:XORG=12.345:YORG=23.456\n'
                    yield dict(kind='transformer',label=f'keyword/trans/{np}/{ns}/{exit}/{angle}/{phase}',parameters=p,native_keyword=True,script=script,stdin='quit\n')
    for turns in [3,5,7]:
        for secondary_width in [3.25,4.375]:
            for angle in [0,17,-35.5]:
                p=dict(name='T',length=160.125,width=3.25,secondary_width=secondary_width,spacing=2.125,turns=turns,metal='M4',secondary_metal='M3',angle=angle,x=12.345,y=23.456)
                script=f'BALUN NAME=T:LEN=160.125:W1=3.25:W2={secondary_width}:S=2.125:N={turns}:METAL=M4:METAL2=M3:ORIENT={angle}:XORG=12.345:YORG=23.456\n'
                yield dict(kind='balun',label=f'keyword/balun/{turns}/{secondary_width}/{angle}',parameters=p,native_keyword=True,script=script,stdin='quit\n')
    for p,labels in [(dict(name='tx'),'NAME=tx'),(dict(primary_name='aa'),'PNAME=aa'),(dict(name='tx',secondary_name='bb'),'NAME=tx:SNAME=bb'),(dict(primary_name='aa',secondary_name='aa'),'PNAME=aa:SNAME=aa')]:
        p.update(length=160.125,width=3.25,spacing=2.125,turns=1.74999999)
        yield dict(kind='transformer',label='defaults/trans/'+labels,parameters=p,native_keyword=True,script=f'TRANS {labels}:LEN=160.125:W=3.25:S=2.125:N=1.74999999\n',stdin='quit\n')
    p=dict(primary_name='A',secondary_name='B',length=160.125,width=3.25,secondary_width=10.125,spacing=2.125,turns=1.5,phase=0)
    yield dict(kind='transformer',label='keyword/trans/ignored-secondary-width',parameters=p,native_keyword=True,script='TRANS PNAME=A:SNAME=B:LEN=160.125:WP=3.25:WS=10.125:S=2.125:N=1.5:PHASE=0\n',stdin='quit\n')
    for turns in [4.99999999,4.9999995,5.00000001]:
        p=dict(name='lower',length=160.125,width=3.25,spacing=2.125,turns=turns)
        yield dict(kind='balun',label=f'defaults/balun/{turns}',parameters=p,native_keyword=True,script=f'BALUN NAME=lower:LEN=160.125:W1=3.25:S=2.125:N={turns}\n',stdin='quit\n')
    for turns in [1.25,1.75,2.75,6.25]:
        p=dict(primary_name='A',secondary_name='B',length=160.123456789,height=140.987654321,width=3.14159265358979,spacing=2.71828182845905,turns=turns,metal='M4',exit_metal='M3',x=12.3456789,y=23.456789)
        answers=f'A\nB\n160.123456789 140.987654321\n3.14159265358979\n2.71828182845905\n{turns}\nM4\ny\nM3\n12.3456789 23.456789\nquit\n'
        yield dict(kind='transformer',label=f'interactive/trans/{turns}',parameters=p,native_keyword=False,native_interactive=True,script='TRANS\n',stdin=answers)
    for turns in [3,5.25,13.75]:
        p=dict(name='T',length=160.123456789,width=3.14159265358979,secondary_width=4.12345678901234,spacing=2.71828182845905,turns=turns,metal='M4',secondary_metal='M3',x=12.3456789,y=23.456789)
        answers=f'T\n160.123456789\n3.14159265358979\n2.71828182845905\n4.12345678901234\n{turns}\nM4\nM3\n12.3456789 23.456789\nquit\n'
        yield dict(kind='balun',label=f'interactive/balun/{turns}',parameters=p,native_keyword=False,native_interactive=True,script='BALUN\n',stdin=answers)

    for turns in [1,2,0,-2,5]:
        p=dict(name='T',length=160.125,width=3.25,spacing=2.125,turns=turns,metal='M4')
        script=f'BALUN NAME=T:LEN=160.125:W1=3.25:S=2.125:N={turns}:METAL=M4\n'
        yield dict(kind='balun',label=f'keyword/balun/default-same-metal/{turns}',parameters=p,native_keyword=True,script=script,stdin='quit\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);args=parser.parse_args()
    ref=args.reference.resolve();original=ref/'run/asitic.linux.2.2';legacy=ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,want in [(original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
    tech=(ref/'run/tek/CMOS.tek').read_text();records=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-paired-')as d:
        for i,c in enumerate(jobs()):
            work=Path(d)/str(i);work.mkdir();commands=COMMANDS.replace('ENTRY',hex(0x80576d4 if c['kind']=='transformer'else 0x8059854)).replace('KIND',repr(c['kind']))
            for name,text in [('process.tek',tech),('input.asit',c['script']),('answers.txt',c['stdin']),('capture.gdb',commands)]:(work/name).write_text(text)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'paired.json').exists():raise RuntimeError(f'Original paired {i} failed: '+run.stdout[-1800:]+run.stderr[-1000:])
            raw=json.loads((work/'paired.json').read_text());assert raw['control_before']==raw['control_after']==0x37f
            records.append(dict(c,stdout=run.stdout,**raw));print(f'Original paired {i}: {c["label"]}',flush=True)
    out=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,technology=tech,gdb_commands=COMMANDS,reference='Unchanged original paired constructor input descriptors and both completed windings, after lead/origin shifts, rotation/reflection/list/direction changes and reciprocal partner links. All XYZ/origin bits, widths, conductor thicknesses, metals and defined via counts; uninitialized conductor mesh counts and via thickness excluded.',cases=records)
    (ROOT/'tests/fixtures/paired_original.json').write_text(json.dumps(out,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
