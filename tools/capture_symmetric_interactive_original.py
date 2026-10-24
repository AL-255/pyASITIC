"""Observe intact original symmetric prompts, retained history and geometry."""
import argparse,hashlib,json,os,re,subprocess,tempfile
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
import gdb,json,struct
records={};scan_count=0;scans=[];bounded_stop=False
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def reg(k):return int(gdb.parse_and_eval('$'+k))&0xffffffff
def u32(a):return struct.unpack('<I',mem(a,4))[0]
def i32(a):return struct.unpack('<i',mem(a,4))[0]
def f64(a):return struct.unpack('<d',mem(a,8))[0]
def name(a):return mem(a,80).split(b'\0')[0].decode('latin1')
class Scan(gdb.Breakpoint):
 def stop(self):
  global scan_count,bounded_stop
  scan_count+=1;esp=reg('esp');scans.append(dict(text=name(u32(esp+4)),format=name(u32(esp+8))))
  if len(scans)>16:scans.pop(0)
  if scan_count>=1200:bounded_stop=True;return True
  return False
class Entry(gdb.Breakpoint):
 def stop(self):
  a=u32(reg('esp')+4);key=name(a)
  records[key]=dict(config={k:f64(a+o)for k,o in [('x',0x54),('y',0x5c),('length',0x70),('height',0x78),('radius',0x80),('width',0x88),('spacing',0x90),('turns',0x98),('angle',0xa0)]},control_before=reg('fctrl'))
  records[key]['config'].update(name=key,sides=i32(a+0x64),metal=i32(a+0x68),secondary_metal=i32(a+0x6c),phase=i32(a+0xac))
  return False
class Return(gdb.Breakpoint):
 def stop(self):
  a=u32(0x80ce558);item=records[name(a)];item.update(origin=[f64(a+0x54),f64(a+0x5c)],origin_bits=mem(a+0x54,16).hex(),segments=[],control_after=reg('fctrl'));s=u32(a+0xa8);metals=i32(0x80d8904)
  while s:
   assert len(item['segments'])<20000
   metal=i32(s+0xdc);r=dict(coordinates_bits=b''.join(mem(s+o,24)for o in(0,24,0x44,0x5c,0x88,0xa0)).hex(),width_bits=mem(s+0xcc,8).hex(),metal=metal)
   if metal<metals:r['thickness_bits']=mem(s+0xd4,8).hex()
   else:r.update(nx=i32(s+0xe0),ny=i32(s+0xe4))
   item['segments'].append(r);s=u32(s+0xec)
  return False
for a in(0x8059854,0x805a45c):Entry('*'+hex(a),internal=True)
for a in(0x805a2fb,0x805abea):Return('*'+hex(a),internal=True)
Scan('*0x804ac94',internal=True)
end
run -g -t process.tek -x input.asit < answers.txt
python
signal=0
if gdb.selected_inferior().pid:
 if not bounded_stop:signal=int(gdb.parse_and_eval('$_siginfo.si_signo'))
 gdb.execute('kill',to_string=True)
open('observed.json','w').write(json.dumps(dict(records=records,signal=signal,bounded_stop=bounded_stop,scan_count=scan_count,last_scans=scans)))
end
quit
'''


def cases(minimum):
    for kind,command in [('symmetric_square','SYMSQ'),('symmetric_polygon','SYMPOLY')]:
        variations=[(3.14159265358979,2.71828182845905,g,n,sides)for g in [None,-.1,0,.1,15.123456789]for n,sides in [(1.999999999,5),(2.999999999,6)]]if not minimum else[(3.14159265358979,s,g,n,6)for s in [-.1,0,.5,1,2.71828182845905]for g,n in [(None,1.999999999),(15.123456789,2.999999999)]]
        for width,spacing,gap,turns,sides in variations:
            p=dict(width=width,spacing=spacing,turns=turns,metal='M4',secondary_metal='M3',x=12.3456789,y=23.456789)
            p['length'if kind=='symmetric_square'else'radius']=120.123456789 if kind=='symmetric_square'else 60.123456789
            if kind=='symmetric_polygon':
                p['sides']=sides
            if gap is not None:p['inner_gap']=gap
            yield dict(kind=kind,command=command,parameters=p,label=f'{kind}/SMIN={minimum}/S={spacing}/G={gap}/N={turns}/sides={sides}')
        if kind=='symmetric_square':
            for dimension,width,spacing,turns in [(38.,3.,2.,4.999999999),(1.,.05,.01,1.999999999),(None,3.14159265358979,2.71828182845905,2.999999999)]:
                p=dict(name='A',width=width,spacing=spacing,inner_gap=15. if dimension is None else .1 if dimension==1 else 10.,turns=turns,metal='M4',secondary_metal='M3',angle=17,phase=-1,x=0,y=512)
                if dimension is not None:p['length']=dimension
                yield dict(kind=kind,command=command,parameters=p,label=f'{kind}/SMIN={minimum}/dimension={dimension}/N={turns}',default_dimension=dimension is None,failed_prompt=bool(minimum and dimension==1))
        elif not minimum:
            yield dict(kind=kind,command=command,parameters=dict(radius=60.123456789,sides=5,width=3.14159265358979,spacing=2.71828182845905,inner_gap=15.123456789,turns=8.999999999,metal='M4',secondary_metal='M3',angle=17,phase=-1,x=0,y=512),label=f'{kind}/SMIN=0/capacity/8.999999999')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);args=parser.parse_args();ref=args.reference.resolve();original=ref/'run/asitic.linux.2.2'
    for path,want in[(original,ORIGINAL_SHA256),(ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
    base=(ref/'run/tek/CMOS.tek').read_text();output=[];batches=[];failed=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-symmetric-interactive-')as d:
        for index,minimum in enumerate([0,1]):
            tech=base if not minimum else re.sub(r'(?im)^(\s*name\s*=\s*m4\s*)$',r'\1\n SMIN=1\n WMIN=10',base)
            if minimum and'SMIN=1'not in tech:raise RuntimeError('Missing modified original metal')
            items=[];script='';stdin=''
            for i,c in enumerate(cases(minimum)):
                p=c['parameters'];p['name']='A'+str(i);prelude=''
                if minimum and c['kind']=='symmetric_polygon':prelude=f'SYMSQ NAME=H{i}:LEN=120.123456789:W=3:S=2:N=1:METAL=M4:METAL2=M3\n'
                dimension=''if c.get('default_dimension')else format(p.get('length')if c['kind']=='symmetric_square'else p['radius'],'.17g')
                answers=f'{p["name"]}\n{dimension}\n{p["width"]:.17g}\nM4\nM3\n{p["spacing"]:.17g}\n'+(''if'inner_gap'not in p else format(p['inner_gap'],'.17g'))+'\n'
                if c['kind']=='symmetric_polygon':answers+=f'{p["sides"]}\n'
                answers+=f'{p["turns"]:.17g}\n{p["x"]:.17g} {p["y"]:.17g}\n'
                c.update(script=prelude+c['command']+'\n',stdin=answers,native_interactive=True,technology=tech)
                if minimum and c['kind']=='symmetric_polygon'or c.get('failed_prompt'):failed.append(c);continue
                script+=c['script'];stdin+=answers;items.append(c)
            work=Path(d)/str(index);work.mkdir()
            for name,value in [('process.tek',tech),('input.asit',script),('answers.txt',stdin+'quit\n'),('capture.gdb',COMMANDS)]:(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'observed.json').exists():raise RuntimeError('Original prompt capture failed: '+run.stdout[-2000:]+run.stderr[-1400:])
            observed=json.loads((work/'observed.json').read_text());assert not observed['signal']and not observed['bounded_stop']
            for c in items:
                record=observed['records'].get(c['parameters']['name'])
                if record is None:raise RuntimeError('Missing original prompt geometry '+c['label'])
                c.update(record);output.append(c)
            batches.append(dict(technology=tech,script=script,stdin=stdin+'quit\n',stdout=run.stdout));print(f'{len(items)} original interactive histories: SMIN={minimum}',flush=True)
        for index,c in enumerate(failed):
            work=Path(d)/('failed'+str(index));work.mkdir()
            for name,value in [('process.tek',c['technology']),('input.asit',c['script']),('answers.txt',c['stdin']+'quit\n'),('capture.gdb',COMMANDS)]:(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'observed.json').exists():raise RuntimeError('Missing bounded original prompt failure: '+run.stdout[-2000:]+run.stderr[-1000:])
            observed=json.loads((work/'observed.json').read_text());assert observed['bounded_stop']and not observed['signal']and c['parameters']['name']not in observed['records']
            assert ('Error: Dimension exceeds maximum dimension of  0.00.'if c['kind']=='symmetric_polygon'else'Error: Dimension exceeds maximum dimension of  0.50.')in run.stdout
            c.update(observed=observed,stdout=run.stdout);print('Original repeated-prompt history '+c['label'],flush=True)
    result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,reference='Unmodified original interactive symmetric creation. Actual constructor entry/static-return observers capture parsed descriptor and every defined geometry store. SMIN/WMIN cases use actual technology files. Nonzero-SMIN polygons retain their preceding ordinary keyword command and repeated maximum-zero prompt history; a data-only sscanf observer stops observation after 1200 calls, then terminates the captured inferior. This is an observation limit, not a claim of native termination. Numerical instructions, inputs and allocator behavior are not patched.',gdb_commands=COMMANDS,batches=batches,cases=output,failed_cases=failed)
    (ROOT/'tests/fixtures/symmetric_interactive_original.json').write_text(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
