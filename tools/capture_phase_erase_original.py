"""Read-only WHO-entry snapshots of original PHASE and ERASE histories."""
import argparse,copy,gzip,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from capture_spatial_edits_original import COMMANDS as BASE,jobs as generators
from capture_copy_links_original import command as copy_command
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]
COMMANDS=BASE.replace("partner=text(u32(a+0xb4))if u32(a+0xb4)else None,segments=[]", "address=a,partner_address=u32(a+0xb4),segments=[]").replace("  head=u32(0x80ce558);shapes=[]", "  if i32(reg('esp')+4)!=224:return False\n  head=u32(0x80ce558);shapes=[]").replace("  states.append(dict(shapes=shapes,control=reg('fctrl')))", "  names={s['address']:s['name']for s in shapes}\n  for s in shapes:s.update(partner=names.get(s['partner_address']),dangling_partner=bool(s['partner_address']and s['partner_address']not in names))\n  states.append(dict(shapes=shapes,control=reg('fctrl')))").replace("Observe('*0x804c620'", "Observe('*0x805bd40'")

def jobs():
 for c in generators():
  if '/edges/'in c['label']:continue
  c=copy.deepcopy(c);n=len(c['names']);ops=[dict(command='PHASE',winding=0,phase=v)for v in(-1,-1,2,7,-2,0,-1,1)]
  ops +=[dict(command='COPY',winding=0,name='c'),dict(command='PHASE',winding=n,phase=-1)]
  if c['label']in('transformer','balun'):ops.append(dict(command='UNFRIEND',winding=0,other=1))
  ops +=[dict(command='BEFRIEND',winding=0,other=n),dict(command='ERASE',windings=[0]),dict(command='MOVE',winding=n-1,x=.125,y=-.25),dict(command='RENAME',winding=n-1,name='final'),dict(command='ERASE',windings=list(range(n)))]
  c['operations']=ops;yield c
 base=copy.deepcopy(next(c for c in generators()if c['label']=='wire'))
 for label,ops in [
  ('erase-directed',[dict(command='COPY',winding=0,name='b'),dict(command='COPY',winding=0,name='c'),dict(command='BEFRIEND',winding=0,other=1),dict(command='BEFRIEND',winding=0,other=2),dict(command='ERASE',windings=[0]),dict(command='MOVE',winding=0,x=.125,y=-.25),dict(command='COPY',winding=1,name='d'),dict(command='MOVE',winding=0,x=1,y=2)]),
  ('erase-mutual',[dict(command='COPY',winding=0,name='b'),dict(command='BEFRIEND',winding=0,other=1),dict(command='ERASE',windings=[1,0])]),
  ('erase-self',[dict(command='BEFRIEND',winding=0,other=0),dict(command='ERASE',windings=[0])])]:
  c=copy.deepcopy(base);c['label']=label;c['operations']=ops;yield c

def command(op,names):
 if op['command']=='PHASE':return f"PHASE {names[op.get('winding',0)]} {op['phase']}\n"
 if op['command']=='ERASE':return 'ERASE '+' '.join(names[i]for i in op['windings'])+'\n'
 return copy_command(op,names)

def main(*,output_name='phase_erase_original',job_source=jobs,description=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args();ref=a.reference.resolve();original=ref/'run/asitic.linux.2.2'
 for path,want in((original,ORIGINAL_SHA256),(ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
  if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
 records=[];parents={}
 with tempfile.TemporaryDirectory(prefix='pyasitic-phase-erase-')as directory:
  for c in job_source():
   parents[c['parent']]=hashlib.sha256((ROOT/'tests/fixtures'/f"{c['parent']}.json").read_bytes()).hexdigest();names=c['names'].copy();script=c['creation']+'WHO\n'
   for op in c['operations']:
    script+=command(op,names)+'WHO\n'
    if op['command']=='COPY':names.append(op['name'].upper())
    elif op['command']=='RENAME':names[op['winding']]=op['name'].upper()
    elif op['command']=='ERASE'and not op.get('expect_rejection',False):names=[name for i,name in enumerate(names)if i not in op['windings']]
   work=Path(directory)/str(len(records));work.mkdir()
   for name,value in(('process.tek',c['technology']),('input.asit',script),('answers.txt',c['stdin']),('capture.gdb',COMMANDS)):(work/name).write_text(value)
   run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
   if run.returncode or not(work/'spatial.json').exists()or'Python Exception'in run.stderr:raise RuntimeError(c['label']+run.stdout[-1500:]+run.stderr[-1000:])
   observed=json.loads((work/'spatial.json').read_text());records.append(dict(c,script=script,stdout=run.stdout,stderr=run.stderr,**observed));print(c['label'],len(observed['states']),'states, signal',observed['signal'],flush=True)
 result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents=parents,gdb_commands=COMMANDS,reference=description or 'Unchanged original PHASE and ERASE command histories, all twelve generators, zero/sticky phases and copied/relinked/deleted scenes. Read-only dispatcher entry snapshots on WHO retain live descriptor addresses, raw phase words, ordered geometry and raw friend addresses without dereferencing freed descriptors. Empty scenes and all selected outcomes retained.',cases=records)
 with gzip.GzipFile(str(ROOT/'tests/fixtures'/f'{output_name}.json.gz'),'wb',mtime=0)as out:out.write((json.dumps(result,separators=(',',':'),allow_nan=False)+'\n').encode())
if __name__=='__main__':main()
