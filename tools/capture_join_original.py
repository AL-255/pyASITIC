"""Unchanged original JOIN histories, translated records and descriptor reuse."""
import argparse,copy,gzip,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from capture_phase_erase_original import COMMANDS as BASE,generators,command as earlier_command
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]
COMMANDS=BASE.replace('native_kind=i32(a+0x50),attributes=',"native_kind=i32(a+0x50),native_n=i32(a+0x64),descriptor_metal=i32(a+0x68),descriptor_exit=i32(a+0x6c),turns_bits=mem(a+0x98,8).hex(),attributes=")

def jobs():
 bases=[c for c in generators()if '/edges/'not in c['label']]
 for base in bases:
  c=copy.deepcopy(base);n=len(c['names']);c['label']='series/'+c['label']
  ops=[dict(command='COPY',winding=0,name='c'),dict(command='MOVETO',winding=n,x=40.123456789,y=70.987654321),dict(command='PHASE',winding=n,phase=-1),dict(command='JOIN',winding=0,others=[n])]
  if base['label']=='via':ops[-1]['expect_rejection']=True
  else:ops.extend([dict(command='MOVE',winding=0,x=.125,y=-.25),dict(command='COPY',winding=0,name='d'),dict(command='FLIP',winding=n),dict(command='JOIN',winding=0,others=[n]),dict(command='ROTATE',winding=0,angle=17.123456789)])
  c['operations']=ops;yield c
 for base in bases:
  if len(base['names'])!=2:continue
  c=copy.deepcopy(base);c['label']='partners/'+c['label'];c['operations']=[dict(command='JOIN',winding=0,others=[1]),dict(command='MOVE',winding=0,x=.125,y=-.25),dict(command='COPY',winding=0,name='d'),dict(command='FLIP',winding=0),dict(command='MOVE',winding=0,x=1,y=2),dict(command='MOVETO',winding=0,x=40.123456789,y=50.987654321),dict(command='PHASE',winding=0,phase=-1)];yield c
 wire=next(c for c in bases if c['label']=='wire')
 c=copy.deepcopy(wire);c['label']='duplicates';c['operations']=[dict(command='COPY',name='b'),dict(command='COPY',name='c'),dict(command='JOIN',winding=0,others=[1,1],expect_rejection=True),dict(command='JOIN',winding=0,others=[0],expect_rejection=True),dict(command='JOIN',winding=0,others=[1,2])];yield c
 for count in(11,12,15):
  c=copy.deepcopy(wire);c['label']=f'argument-count/{count}';c['operations']=[dict(command='COPY',name=f'r{i}')for i in range(1,count)]
  c['operations'].append(dict(command='JOIN',winding=0,others=list(range(1,count)),**({'expect_rejection':True}if count>12 else{})));yield c
 # Converting a copied VIA's stored metal leaves kind14 intact; the native
 # JOIN then indexes its via table with that metal and may fault.
 c=copy.deepcopy(next(c for c in bases if c['label']=='via'));c['label']='via-copied-metal';c['operations']=[dict(command='COPY',name='c',metal='M2'),dict(command='JOIN',winding=0,others=[1],expect_rejection=True)];yield c

def command(op,names):
 if op['command']=='JOIN':return 'JOIN '+' '.join(names[i]for i in[op.get('winding',0),*op['others']])+'\n'
 return earlier_command(dict(op,winding=op.get('winding',0)),names)

def update_names(names,op):
 if op.get('expect_rejection',False):return
 if op['command']=='COPY':names.append(op['name'].upper())
 elif op['command']=='JOIN':names[:]=[name for i,name in enumerate(names)if i not in op['others']]
 elif op['command']=='RENAME':names[op.get('winding',0)]=op['name'].upper()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args();ref=a.reference.resolve();original=ref/'run/asitic.linux.2.2'
 for path,want in((original,ORIGINAL_SHA256),(ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
  if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
 cases=[];parents={}
 with tempfile.TemporaryDirectory(prefix='pyasitic-original-join-')as directory:
  for c in jobs():
   parents[c['parent']]=hashlib.sha256((ROOT/'tests/fixtures'/f"{c['parent']}.json").read_bytes()).hexdigest();names=c['names'].copy();script=c['creation']+'WHO\n'
   for op in c['operations']:script+=command(op,names)+'WHO\n';update_names(names,op)
   work=Path(directory)/str(len(cases));work.mkdir()
   for name,value in(('process.tek',c['technology']),('input.asit',script),('answers.txt',c['stdin']),('capture.gdb',COMMANDS)):(work/name).write_text(value)
   r=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
   if r.returncode or not(work/'spatial.json').exists()or'Python Exception'in r.stderr:raise RuntimeError(c['label']+r.stdout[-1500:]+r.stderr[-1000:])
   observed=json.loads((work/'spatial.json').read_text());cases.append(dict(c,script=script,stdout=r.stdout,stderr=r.stderr,**observed));print(c['label'],len(observed['states']),'states; signal',observed['signal'],flush=True)
 result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents=parents,gdb_commands=COMMANDS,reference='Unchanged original JOIN command histories after all twelve generators, translated copied records, reversals/phase, paired stale links and descriptor reuse, duplicate and argument-count parser rejections, and VIA compatibility/copy-metal behavior. Read-only WHO-entry snapshots retain every selected state and fault. No numerical instructions, allocator callbacks or output words replaced.',cases=cases)
 with gzip.GzipFile(str(ROOT/'tests/fixtures/join_original.json.gz'),'wb',mtime=0)as f:f.write((json.dumps(result,separators=(',',':'),allow_nan=False)+'\n').encode())
if __name__=='__main__':main()
