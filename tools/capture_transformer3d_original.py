"""Capture intact-original 3D prompt descriptors and both completed windings."""
import argparse,hashlib,json,math,os,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]
COMMANDS=r'''
set pagination off
set confirm off
set environment TERM dumb
set environment INPUTRC /dev/null
break *0x8057d40
run -g -t process.tek -x input.asit < answers.txt
python
import gdb,struct,json
def memory(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def u32(a):return struct.unpack('<I',memory(a,4))[0]
def i32(a):return struct.unpack('<i',memory(a,4))[0]
def f64(a):return struct.unpack('<d',memory(a,8))[0]
def name(a):return memory(a,80).split(b'\0')[0].decode('latin1')
def config(a):return dict(name=name(a),length=f64(a+0x70),height=f64(a+0x78),width=f64(a+0x88),spacing=f64(a+0x90),turns=f64(a+0x98),angle=f64(a+0xa0),metal=i32(a+0x68),phase=i32(a+0xac),origin_bits=memory(a+0x54,16).hex(),x=f64(a+0x54),y=f64(a+0x5c))
control_before=int(gdb.parse_and_eval('$fctrl'));esp=int(gdb.parse_and_eval('$esp'));ret=u32(esp)
configs=[config(u32(esp+4)),config(u32(esp+8))]
gdb.breakpoints()[0].enabled=False
gdb.Breakpoint('*'+hex(ret),temporary=True,internal=True);gdb.execute('continue',to_string=True)
head=u32(0x80ce558);other=u32(head+0xb0)
assert head and other
metal_count=i32(0x80d8904)
def record(a):
 out=dict(name=name(a),origin=[f64(a+0x54),f64(a+0x5c)],origin_bits=memory(a+0x54,16).hex(),auxiliary=u32(a+0xb4),segments=[])
 s=u32(a+0xa8)
 while s:
  assert len(out['segments'])<20000
  m=i32(s+0xdc);assert 0<=m<metal_count
  out['segments'].append(dict(coordinates_bits=b''.join(memory(s+o,24)for o in(0,24,0x44,0x5c,0x88,0xa0)).hex(),width_bits=memory(s+0xcc,8).hex(),thickness_bits=memory(s+0xd4,8).hex(),primary_width_bits=memory(s+0x30,8).hex(),primary_thickness_bits=memory(s+0x38,8).hex(),metal=m))
  s=u32(s+0xec)
 return out
out=dict(configs=configs,windings=[record(other),record(head)],control_before=control_before,control_after=int(gdb.parse_and_eval('$fctrl')))
open('3d.json','w').write(json.dumps(out))
end
kill
quit
'''


def jobs():
    turns=[1,math.nextafter(1,math.inf),math.nextafter(1.25,-math.inf),1.25,1.5,1.75,math.nextafter(2,-math.inf),2,2.25,2.5,2.75,3.2,3.75]
    for n in turns:
        for first,second in [('M4','M3'),('M5','M1'),('M1','M5')]:
            for angle,phase in [(0,1),(37.123456789,-1)]:
                p=dict(primary_name='P',secondary_name='S',length=160.123456789,height=140.987654321,width=3.14159265358979,spacing=8.2718281828459,turns=n,metal=first,secondary_metal=second,x=12.3456789,y=23.456789,angle=angle,phase=phase)
                yield f'turn/{n}/{first}/{second}/{angle}/{phase}',p,{}
    base=dict(primary_name='p',secondary_name='s',length=80,height=70,width=3,spacing=8,turns=1.25,metal='M4',secondary_metal='M3',x=10,y=20,angle=0,phase=1)
    for label,change in [('negative-length',dict(length=-100)),('zero-height',dict(height=0)),('both-zero',dict(length=0,height=0)),('both-negative',dict(length=-100,height=-50)),('outside-origin',dict(x=-42.123456789,y=1000.987654321)),('signed-zero-origin',dict(x=-0.,y=-0.)),('orientation-360',dict(angle=360)),('orientation-minus360',dict(angle=-360)),('phase-truncation',dict(phase=-1.875)),('name-tokens',dict(primary_name='lower primary',secondary_name='other secondary')),('duplicate-names',dict(primary_name='same',secondary_name='same'))]:
        yield label,dict(base,**change),{}
    boundaries=[(42.871544184110704,20.585793601058654,True),(56.46757780078548,26.217270725085346,True),(53.1488395139861,24.842649326693042,True),(92.47130085598607,41.13001281454943,False),(65.9779747260938,30.156477131548055,True),(24.89344847040179,13.139266356440421,False)]
    for i,(w,s,valid)in enumerate(boundaries):
        # Rejected prompt values are followed by a valid value; record the
        # accepted descriptor and the original retry transcript independently.
        p=dict(base,length=400,height=350,width=w,spacing=s if valid else 100)
        yield f'spacing-boundary/{i}/{valid}',p,dict(spacing_input=[s]if valid else[s,100],attempted_spacing=s,accepted=valid)
    yield 'prompt-retries',base,dict(width_input=[0,3],spacing_input=[0,8],turns_input=[.5,1.25],secondary_metal_input=['M4','M3'],angle_input=[361,0],phase_input=[0,1])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);args=parser.parse_args()
    ref=args.reference.resolve();original=ref/'run/asitic.linux.2.2';legacy=ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,want in [(original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
    technology=(ref/'run/tek/CMOS.tek').read_text();cases=[];invalid=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-3d-')as d:
        for i,(label,p,extra)in enumerate(jobs()):
            lines=[p['primary_name'],p['secondary_name'],f"{p['length']} {p['height']}"]
            for key in ['width','spacing','turns','metal','secondary_metal']:lines.extend(map(str,extra.get(key+'_input',[p[key]])))
            lines.append(f"{p['x']} {p['y']}")
            for key in ['angle','phase']:lines.extend(map(str,extra.get(key+'_input',[p[key]])))
            answers='\n'.join(lines+['quit'])+'\n';script='3DMIRRORTRANS\n';work=Path(d)/str(i);work.mkdir()
            for name,value in [('process.tek',technology),('input.asit',script),('answers.txt',answers),('capture.gdb',COMMANDS)]:(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'3d.json').exists():raise RuntimeError(f'Original 3D {i}/{label} failed: '+run.stdout[-1600:]+run.stderr[-1200:])
            raw=json.loads((work/'3d.json').read_text());assert raw['control_before']==raw['control_after']==0x37f
            cases.append(dict(label=label,parameters=p,native_interactive=True,script=script,stdin=answers,stdout=run.stdout,**extra,**raw));print(f'Original 3D {i}: {label}',flush=True)
        for alias in ['3DMIRRORTRANS','3DTrans','Trans3D','TransMIM']:
            for arguments in ['NAME=T','PNAME=A:SNAME=B','LEN=80:W=3']:
                work=Path(d)/f'invalid-{len(invalid)}';work.mkdir();script=f'{alias} {arguments}\n'
                (work/'process.tek').write_text(technology);(work/'input.asit').write_text(script)
                run=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path,TERM='dumb',INPUTRC='/dev/null'),input='quit\n',capture_output=True,text=True,start_new_session=True,timeout=30)
                if run.returncode or not any(t in run.stdout for t in ['Invalid Argument(s):','Unknown or Mistyped Commnd'])or 'Primary Name?'in run.stdout:raise RuntimeError('Original 3D keyword behavior changed: '+run.stdout[-900:])
                invalid.append(dict(script=script,stdin='quit\n',returncode=run.returncode,stdout=run.stdout,stderr=run.stderr))
    out=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,technology=technology,gdb_commands=COMMANDS,reference='Intact original 3DMIRRORTRANS prompt descriptors at entry 0x08057d40 and actual returned winding records. Exact XYZ/origin/width/thickness/primary-width/primary-thickness/metal fields; unwritten mesh counts excluded. No numerical instructions, allocation hooks, descriptor inputs or command metadata patched.',cases=cases,invalid_keywords=invalid)
    (ROOT/'tests/fixtures/transformer3d_original.json').write_text(json.dumps(out,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
