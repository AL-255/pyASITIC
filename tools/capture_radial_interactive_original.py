"""Unchanged original interactive SPIRAL/RING histories and radial edge cases."""
import argparse,gzip,hashlib,json,math,os,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]
COMMANDS=r'''
set pagination off
set confirm off
set environment TERM dumb
set environment INPUTRC /dev/null
handle SIGQUIT nostop noprint pass
break *CREATOR
run -g -t process.tek -x input.asit < answers.txt
python
import gdb,struct,json
result=dict(entered=bool(gdb.selected_inferior().pid),segments=[],signal=0,returned=False)
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def reg(k):return int(gdb.parse_and_eval('$'+k))&0xffffffff
def u32(a):return struct.unpack('<I',mem(a,4))[0]
def i32(a):return struct.unpack('<i',mem(a,4))[0]
def text(a):return gdb.Value(a).cast(gdb.lookup_type('char').pointer()).string()
if result['entered']:
 esp=reg('esp');ret=u32(esp);args=u32(esp+4);kind=i32(args+0x50)
 offsets=dict(radius=0x80,width=0x88,angle=0xa0,x=0x54,y=0x5c)
 if kind==22:offsets['gap']=0x90
 else:offsets.update(spacing=0x90,turns=0x98)
 result.update(config={k:mem(args+o,8).hex()for k,o in offsets.items()},sides=i32(args+0x64),metal=i32(args+0x68),phase=i32(args+0xac),native_kind=kind,name=text(args),control_before=reg('fctrl'))
 gdb.Breakpoint('*'+hex(ret),temporary=True,internal=True);gdb.execute('continue',to_string=True)
 if not gdb.selected_inferior().pid:pass
 elif reg('pc')!=ret:
  result['signal']=int(gdb.parse_and_eval('$_siginfo.si_signo'))
 else:
  result['returned']=True
  head=u32(0x80ce558);result.update(origin_bits=mem(head+0x54,16).hex(),created_name=text(head));p=u32(head+0xa8)
  while p:
   assert len(result['segments'])<20000
   result['segments'].append(dict(coordinates_bits=b''.join(mem(p+o,24)for o in(0,24,0x44,0x5c,0x88,0xa0)).hex(),width_bits=mem(p+0xcc,8).hex(),thickness_bits=mem(p+0xd4,8).hex(),metal=i32(p+0xdc)));p=u32(p+0xec)
 result['control_after']=reg('fctrl')if gdb.selected_inferior().pid else None
 open('raw.json','w').write(json.dumps(result))
 if gdb.selected_inferior().pid:gdb.execute('kill',to_string=True)
else:open('raw.json','w').write(json.dumps(result))
end
quit
'''

def interactive(kind,p):
 def n(k):return format(p[k],'.17g')
 if kind=='ring':lines=[p['name'],n('radius'),str(p['sides']),n('width'),n('gap'),p['metal']]
 else:lines=[p['name'],str(p['sides']),n('radius'),n('width'),n('spacing'),n('turns'),p['metal']]
 return '\n'.join(lines+[n('x')+' '+n('y'),'quit'])+'\n'

def keyword(p):
 names=dict(radius='RAD',sides='SIDES',width='W',gap='GAP',angle='ORIENT',metal='METAL',phase='PHASE',x='XORG',y='YORG')
 return 'RING NAME='+p['name']+':'+':'.join(names[k]+'='+(format(v,'.17g')if isinstance(v,(int,float))else v)for k,v in p.items()if k in names)+'\n'

def jobs():
 base=dict(name='A',radius=120.123456789,width=3.14159265358979,metal='M4',angle=17,phase=-1,x=12.3456789,y=23.456789)
 for sides in(3,4,7,16,32,128):
  for gap in(0.,.1234567,20.,179.9,360.,720.,1000.):
   p=dict(base,sides=sides,gap=gap);yield 'ring',f'interactive/{sides}/{gap}',p,False,interactive('ring',p)
 for sides in(3,4,8):
  for width in(20.,30.,40.):
   p=dict(base,radius=40.,width=width,sides=sides,gap=20.);yield 'ring',f'interactive/wide/{sides}/{width}',p,False,interactive('ring',p)
 for gap in(-1e-8,-.1,-20.,-360.,-720.25):
  for native_keyword in(False,True):
   p=dict(base,radius=40.,sides=16,gap=gap,angle=0,phase=1);yield 'ring',f'gap-fault/{native_keyword}/{gap}',p,native_keyword,'quit\n'if native_keyword else interactive('ring',p)
 for gap,angle in((720.,0.),(1000.,0.),(720.1234567,17.),(20.,720.),(20.,-720.),(20.,1000.),(20.,-1000.)):
  p=dict(base,radius=40.,sides=16,gap=gap,angle=angle);yield 'ring',f'keyword/wrapped/{gap}/{angle}',p,True,'quit\n'
 for sides in(3,4,7,16,32,128):
  edge=2+1/sides
  for turns in(1.,math.nextafter(edge,-math.inf),edge,math.nextafter(edge,math.inf),edge-1e-8,edge+1e-8):
   p=dict(base,sides=sides,spacing=2.71828182845905,turns=turns);yield 'polygon',f'interactive/{sides}/{turns:.17g}',p,False,interactive('polygon',p)
 for kind in('ring','polygon'):
  for radius in(300.,512.):
   p=dict(base,sides=7,radius=radius,width=20.,gap=20.,spacing=2.,turns=1.,x=0.,y=512.);yield kind,f'interactive/radius/{radius}',p,False,interactive(kind,p)
  for name in('  radial coil  ','r.a-d_ial','MiXeD'):
   p=dict(base,name=name,radius=40.,sides=7,gap=20.,spacing=2.,turns=1.);yield kind,'interactive/name/'+repr(name),p,False,interactive(kind,p)
  p=dict(base,radius=1e-8,width=1e-10,sides=7,gap=20.,spacing=1e-10,turns=1.,x=0.,y=0.)
  yield kind,'interactive/small',p,False,interactive(kind,p)
 p=dict(base,radius=300.,sides=7,gap=20.,angle=0,phase=1);yield 'ring','keyword/oversize',p,True,'quit\n'
 for sides,width in((3,30.),(4,40.),(8,40.)):
  p=dict(base,radius=40.,width=width,sides=sides,gap=20.,angle=0);yield 'ring',f'keyword/wide/{sides}/{width}',p,True,'quit\n'


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args();ref=a.reference.resolve();original=ref/'run/asitic.linux.2.2'
 for path,expected in((original,ORIGINAL_SHA256),(ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
  if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Unexpected original checksum')
 technology=(ROOT/'src/reasitic/CMOS.tek').read_text();records=[]
 with tempfile.TemporaryDirectory(prefix='pyasitic-original-radial-interactive-')as d:
  for index,(kind,label,parameters,native_keyword,answers)in enumerate(jobs()):
   work=Path(d)/str(index);work.mkdir();script=keyword(parameters)if native_keyword else'RING\n'if kind=='ring'else'SPIRAL\n';commands=COMMANDS.replace('CREATOR','0x805b450'if kind=='ring'else'0x8057248')
   for name,value in(('process.tek',technology),('input.asit',script),('answers.txt',answers),('capture.gdb',commands)):(work/name).write_text(value)
   run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
   if run.returncode or not(work/'raw.json').exists()or'Python Exception'in run.stderr or'Traceback'in run.stderr:raise RuntimeError(f'{index}/{label}: '+run.stdout[-2200:]+run.stderr[-1500:])
   records.append(dict(kind=kind,label=label,parameters=parameters,native_keyword=native_keyword,script=script,stdin=answers,stdout=run.stdout,stderr=run.stderr,**json.loads((work/'raw.json').read_text())));r=records[-1];print(index,label,len(r['segments']),'segments','signal',r['signal'],'entered',r['entered'],flush=True)
 result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,technology=technology,gdb_commands=COMMANDS,reference='Unchanged complete original interactive RING/SPIRAL and keyword radial edge histories. Read-only constructor entry/actual-return observations capture defined config, origin, all segment XYZ/width/thickness/metal stores. Original parser rejections and negative-gap construction failures retained. No numerical or runtime replacement.',cases=records)
 with gzip.GzipFile(str(ROOT/'tests/fixtures/radial_interactive_original.json.gz'),'wb',mtime=0)as f:f.write((json.dumps(result,separators=(',',':'),allow_nan=False)+'\n').encode())

if __name__=='__main__':main()
