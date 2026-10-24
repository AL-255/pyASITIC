"""Observe unchanged original spatial-edit command histories for every generator."""
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
python
import gdb,struct,json
states=[]
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def reg(k):return int(gdb.parse_and_eval('$'+k))&0xffffffff
def u32(a):return struct.unpack('<I',mem(a,4))[0]
def i32(a):return struct.unpack('<i',mem(a,4))[0]
def text(a):return mem(a,80).split(b'\0',1)[0].decode('latin1')
def shape(a):
 out=dict(name=text(a),origin_bits=mem(a+0x54,16).hex(),native_kind=i32(a+0x50),attributes=i32(a+0xac),partner=text(u32(a+0xb4))if u32(a+0xb4)else None,segments=[]);s=u32(a+0xa8);metals=i32(0x80d8904)
 while s:
  assert len(out['segments'])<20000;metal=i32(s+0xdc)
  r=dict(coordinates_bits=b''.join(mem(s+o,24)for o in(0,24,0x44,0x5c,0x88,0xa0)).hex(),width_bits=mem(s+0xcc,8).hex(),metal=metal)
  if metal<metals:r.update(thickness_bits=mem(s+0xd4,8).hex(),primary_width_bits=mem(s+0x30,8).hex(),primary_thickness_bits=mem(s+0x38,8).hex())
  else:r.update(nx=i32(s+0xe0),ny=i32(s+0xe4))
  out['segments'].append(r);s=u32(s+0xec)
 return out
class Observe(gdb.Breakpoint):
 def stop(self):
  head=u32(0x80ce558);shapes=[]
  while head:
   assert len(shapes)<100;shapes.append(shape(head));head=u32(head+0xb0)
  states.append(dict(shapes=shapes,control=reg('fctrl')));return False
Observe('*0x804c620',internal=True)
end
run -g -t process.tek -x input.asit < answers.txt
python
signal=0
if gdb.selected_inferior().pid:signal=int(gdb.parse_and_eval('$_siginfo.si_signo'));gdb.execute('kill',to_string=True)
open('spatial.json','w').write(json.dumps(dict(states=states,signal=signal)))
end
quit
'''

def load(name):return json.loads((ROOT/'tests/fixtures'/f'{name}.json').read_text())
def jobs():
 selections=[('square_original','square',lambda c:c['parameters'].get('turns')==1.75 and c['parameters'].get('angle')==17 and c['parameters'].get('exit_metal')=='M3'),
  ('polygon_inputs_original','polygon',lambda c:c['parameters'].get('sides')==7),('ring_original','ring',lambda c:True),
  ('wire_original','wire',lambda c:c.get('native_interactive')and c['parameters']['angle']==37),
  ('primitive_original','capacitor',lambda c:c['kind']=='capacitor'and c.get('native_interactive')),
  ('primitive_original','via',lambda c:c['kind']=='via'and c.get('native_interactive')),
  ('symmetric_geometry_original','symmetric_square',lambda c:c['kind']=='symmetric_square'and c['parameters'].get('turns')==2),
  ('symmetric_geometry_original','symmetric_polygon',lambda c:c['kind']=='symmetric_polygon'),
  ('multimetal_original','multimetal',lambda c:c['parameters'].get('turns')==1.75),
  ('paired_original','transformer',lambda c:c['kind']=='transformer'and c.get('native_interactive')),
  ('paired_original','balun',lambda c:c['kind']=='balun'and c.get('native_interactive')),
  ('transformer3d_original','transformer3d',lambda c:True)]
 for parent,kind,predicate in selections:
  f=load(parent);index,c=next((i,c)for i,c in enumerate(f['cases'])if predicate(c));names=[w['name']for w in c['windings']]if'windings'in c else[c['parameters'].get('name','A')]
  public=dict(kind=kind,parameters=c['parameters'],**{k:c[k]for k in('native_keyword','native_interactive')if k in c})
  if kind=='ring':public['native_keyword']=True
  operations=[dict(command='MOVEX',winding=0,x=.123456789),dict(command='MOVEY',winding=0,y=-.25),dict(command='MOVE',winding=0,x=123.456789,y=-45.67891),dict(command='MOVETO',winding=0,x=40.123456789,y=50.987654321),dict(command='ROTATE',winding=0,angle=0.),dict(command='ROTATE',winding=0,angle=17.123456789),dict(command='FLIPV',winding=0),dict(command='FLIPH',winding=0),dict(command='FLIP',winding=0),dict(command='ROTATE',winding=0,angle=-35.5)]
  if len(names)==2:operations.extend([dict(command='MOVE',winding=1,x=-.05,y=.05),dict(command='MOVETO',winding=1,x=80.987654321,y=90.123456789)])
  yield dict(label=kind,parent=parent,parent_index=index,public=public,technology=f['technology'],creation=c['script'],stdin=c.get('stdin','quit\n'),names=names,operations=operations)
 # Zero and subthreshold command rotations still execute and rebase; default
 # asymmetric negative wrapping, F32 snap boundaries and large origins remain.
 f=load('wire_original');index,c=next((i,c)for i,c in enumerate(f['cases'])if c.get('native_interactive')and c['parameters']['angle']==37)
 for origin in(0.,1e10,-1e10):
  operations=[dict(command='MOVETO',winding=0,x=origin,y=-origin)]
  for angle in(0.,1e-12,-1e-12,360.,-360.,720.123456789,-720.123456789,1000.,-1000.):operations.append(dict(command='ROTATE',winding=0,angle=angle))
  for x in(math.nextafter(.05,0),.05,math.nextafter(.05,math.inf),-.05,math.nextafter(-.05,-math.inf)):
   operations.append(dict(command='MOVE',winding=0,x=x,y=-x))
  yield dict(label=f'wire/edges/{origin}',parent='wire_original',parent_index=index,public=dict(kind='wire',parameters=c['parameters'],native_interactive=True),technology=f['technology'],creation=c['script'],stdin=c['stdin'],names=['A'],operations=operations)

def command(op,names):
 name=names[op['winding']];cmd=op['command'];args=[op[k]for k in(('x','y')if cmd in('MOVE','MOVETO')else('x',)if cmd=='MOVEX'else('y',)if cmd=='MOVEY'else('angle',)if cmd=='ROTATE'else())]
 return ' '.join([cmd,name,*[format(v,'.17g')for v in args]])+'\n'

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args();ref=a.reference.resolve();original=ref/'run/asitic.linux.2.2'
 for path,want in((original,ORIGINAL_SHA256),(ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
  if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
 cases=[];parents={}
 with tempfile.TemporaryDirectory(prefix='pyasitic-original-spatial-edits-')as d:
  for c in jobs():
   parents[c['parent']]=hashlib.sha256((ROOT/'tests/fixtures'/f'{c["parent"]}.json').read_bytes()).hexdigest();script=c['creation']+f'GEOM {c["names"][0]}\n'
   for op in c['operations']:script+=command(op,c['names'])+f'GEOM {c["names"][0]}\n'
   work=Path(d)/str(len(cases));work.mkdir()
   for name,value in(('process.tek',c['technology']),('input.asit',script),('answers.txt',c['stdin']),('capture.gdb',COMMANDS)):(work/name).write_text(value)
   run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
   if run.returncode or not(work/'spatial.json').exists()or'Python Exception'in run.stderr:raise RuntimeError(c['label']+run.stdout[-1500:]+run.stderr[-1000:])
   observed=json.loads((work/'spatial.json').read_text())
   if observed['signal']or len(observed['states'])!=len(c['operations'])+1:raise RuntimeError(c['label']+' incomplete '+repr(observed)+run.stdout[-1200:])
   cases.append(dict(c,script=script,stdout=run.stdout,stderr=run.stderr,**observed));print(c['label'],len(observed['states']),'states',flush=True)
 result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents=parents,gdb_commands=COMMANDS,reference='Unchanged original complete spatial command histories after all twelve generators. Read-only snapshots at GEOM entry capture names, origin, native attributes/kind, friend linkage, ordered XYZ/ribbon/material/width/thickness/via stores after every operation. No numerical instructions or runtime replacements. Default SNAP and type7/type10 parsing retained, including zero/subthreshold rotations and large-origin stores.',cases=cases)
 with gzip.GzipFile(str(ROOT/'tests/fixtures/spatial_edits_original.json.gz'),'wb',mtime=0)as out:out.write((json.dumps(result,separators=(',',':'),allow_nan=False)+'\n').encode())

if __name__=='__main__':main()
