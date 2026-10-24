"""Observe original symmetric keyword clearance stores and actual decisions."""
import argparse,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]
COMMANDS=r'''
set pagination off
set confirm off
set environment TERM dumb
set environment INPUTRC /dev/null
handle SIGQUIT nostop noprint pass
python
import gdb,struct,json
records={}
def memory(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def u32(a):return struct.unpack('<I',memory(a,4))[0]
def i32(a):return struct.unpack('<i',memory(a,4))[0]
def f64(a):return struct.unpack('<d',memory(a,8))[0]
def name(a):return memory(a,80).split(b'\0')[0].decode('latin1')
def reg(k):return int(gdb.parse_and_eval('$'+k))&0xffffffff
def raw(k):return bytes(gdb.parse_and_eval('$st'+str(k)).bytes).hex()
points={0x80851c8:'start',0x80851e4:'radius80',0x80851f6:'angle80',0x8085242:'acos80',0x808526e:'half80',0x8085272:'tan80',0x808528a:'compare80',0x8085291:'decision',0x8085932:'start',0x808594e:'radius80',0x8085960:'angle80',0x80859ac:'acos80',0x80859d8:'half80',0x80859dc:'tan80',0x80859f4:'compare80',0x80859fb:'decision'}
class Point(gdb.Breakpoint):
 def stop(self):
  address=reg('pc');kind=points[address];shape=reg('edi');key=name(shape);item=records.setdefault(key,dict(points={}))
  if kind=='start':
   ebp=reg('ebp');gap=struct.unpack('<f',memory(ebp-4,4))[0]
   item.update(width_bits=memory(shape+0x88,8).hex(),spacing_bits=memory(shape+0x90,8).hex(),gap_bits=struct.pack('<d',gap).hex(),control_before=reg('fctrl'))
  elif kind=='decision':item.update(reject=((reg('eax')>>8)&0x45)==0,comparison_mask=(reg('eax')>>8)&0x45,control_after=reg('fctrl'))
  elif kind=='compare80':item['points'][kind]=[raw(0),raw(1)]
  else:
   item['points'][kind]=raw(0)
   if kind=='angle80':item['radius_bits']=memory(reg('ebp')-0x240,8).hex()
   if kind=='half80':item['acos_bits']=memory(reg('ebp')-0x240,8).hex()
   if kind=='compare80':item['tangent_bits']=memory(reg('ebp')-0x238,8).hex()
  if kind=='compare80':item['tangent_bits']=memory(reg('ebp')-0x238,8).hex()
  return False
class Creator(gdb.Breakpoint):
 def stop(self):
  shape=u32(reg('esp')+4);key=name(shape);item=records.setdefault(key,dict(points={}))
  item.update(accepted=True,config=dict(name=key,length=f64(shape+0x70),height=f64(shape+0x78),width=f64(shape+0x88),spacing=f64(shape+0x90),turns=f64(shape+0x98),radius=f64(shape+0x80),sides=i32(shape+0x64),metal=i32(shape+0x68),secondary_metal=i32(shape+0x6c),phase=i32(shape+0xac),angle=f64(shape+0xa0),x=f64(shape+0x54),y=f64(shape+0x5c)))
  return False
class Geometry(gdb.Breakpoint):
 def stop(self):
  shape=u32(0x80ce558);key=name(shape);item=records[key];metal_count=i32(0x80d8904)
  item.update(origin=[f64(shape+0x54),f64(shape+0x5c)],origin_bits=memory(shape+0x54,16).hex(),segments=[],geometry_control=reg('fctrl'))
  segment=u32(shape+0xa8)
  while segment:
   assert len(item['segments'])<20000
   metal=i32(segment+0xdc);r=dict(coordinates_bits=b''.join(memory(segment+o,24)for o in(0,24,0x44,0x5c,0x88,0xa0)).hex(),width_bits=memory(segment+0xcc,8).hex(),metal=metal)
   if metal<metal_count:r['thickness_bits']=memory(segment+0xd4,8).hex()
   else:r.update(nx=i32(segment+0xe0),ny=i32(segment+0xe4))
   item['segments'].append(r);segment=u32(segment+0xec)
  return False
for address in [0x805a2fb,0x805abea]:Geometry('*'+hex(address),internal=True)
for address in points:Point('*'+hex(address),internal=True)
for address in [0x8059854,0x805a45c]:Creator('*'+hex(address),internal=True)
end
run -g -t process.tek -x input.asit < answers.txt
python
signal=0
if gdb.selected_inferior().pid:signal=int(gdb.parse_and_eval('$_siginfo.si_signo'));gdb.execute('kill',to_string=True)
open('transition.json','w').write(json.dumps(dict(records=records,signal=signal)))
end
quit
'''


def jobs():
    for kind,command,dimension in [('symmetric_square','SYMSQ','LEN=480'),('symmetric_polygon','SYMPOLY','RAD=240:SIDES=6')]:
        for w in [1,2,3,5,10]:
            for s in [0,.1,.5,1,2,5]:
                for g in [None,-10,-3,-.1,0,.1,.5,1,2,3,5,10,15,30]:
                    p=dict(width=w,spacing=s,turns=1,metal='M4',secondary_metal='M3',x=40,y=40)
                    p['length'if kind=='symmetric_square'else'radius']=480 if kind=='symmetric_square'else 240
                    if kind=='symmetric_polygon':p['sides']=6
                    if g is not None:p['inner_gap']=g
                    yield dict(kind=kind,command=command,dimension=dimension,parameters=p,label=f'{kind}/{w}/{s}/{g}')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);args=parser.parse_args()
    ref=args.reference.resolve();original=ref/'run/asitic.linux.2.2';legacy=ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,want in [(original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
    technology=(ref/'run/tek/CMOS.tek').read_text();cases=[];script=''
    for i,c in enumerate(jobs()):
        p=dict(c['parameters'],name='A'+str(i));line=f'{c["command"]} NAME={p["name"]}:{c["dimension"]}:W={p["width"]}:S={p["spacing"]}:N=1:METAL=M4:METAL2=M3:XORG=40:YORG=40'
        if 'inner_gap'in p:line+=f':ILEN={p["inner_gap"]}'
        line+='\n';script+=line;cases.append(dict(kind=c['kind'],label=c['label'],parameters=p,native_keyword=True,script=line))
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-transition-')as d:
        work=Path(d)
        for name,value in [('process.tek',technology),('input.asit',script),('answers.txt','quit\n'),('capture.gdb',COMMANDS)]:(work/name).write_text(value)
        run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=180)
        if run.returncode or not(work/'transition.json').exists():raise RuntimeError(run.stdout[-1800:]+run.stderr[-1000:])
        observed=json.loads((work/'transition.json').read_text())
        if observed['signal']:raise RuntimeError('Original batch fault: '+run.stdout[-1500:]+run.stderr[-1800:])
        for c in cases:
            r=observed['records'].get(c['parameters']['name'])
            if r is None:raise RuntimeError('Missing original transition case '+c['label'])
            if 'inner_gap'in c['parameters']:
                if 'reject'not in r or r['control_before']!=0x37f or r['control_after']!=0x37f:raise RuntimeError('Missing original comparison '+c['label'])
                if r.get('accepted',False)==r['reject']:raise RuntimeError('Original validation/creation disagreement '+c['label'])
            c.update(r);c.setdefault('accepted',False)
    out=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,technology=technology,gdb_commands=COMMANDS,script=script,stdout=run.stdout,reference='Unmodified original symmetric keyword parser instruction-point observations and actual constructor entry acceptance. Retained operands, all defined binary64 radius/acos/tangent stores and x87 comparison masks observed without patching numerical code, inputs, allocations or parser metadata.',cases=cases)
    (ROOT/'tests/fixtures/transition_original.json').write_text(json.dumps(out,separators=(',',':'),allow_nan=False)+'\n')
    print(f'{len(cases)} original transition cases: {sum(c["accepted"]for c in cases)} accepted, {sum(not c["accepted"]for c in cases)} rejected')


if __name__=='__main__':main()
