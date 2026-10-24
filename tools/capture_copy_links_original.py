"""Unchanged original COPY/RENAME/BEFRIEND/UNFRIEND command histories."""
import argparse,copy,gzip,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
from capture_spatial_edits_original import COMMANDS,jobs as spatial_jobs,command as spatial_command,ROOT


def jobs():
 for source in spatial_jobs():
  if '/edges/'in source['label']:continue
  c=copy.deepcopy(source);n=len(c['names']);c['operations']=[
   dict(command='COPY',winding=0,name='copy_1'),dict(command='COPY',winding=0,name='copy_2',metal='M2',x=12.3456789,y=23.456789),
   dict(command='RENAME',winding=n,name='renamed'),dict(command='MOVE',winding=n,x=.123456789,y=.234567891),
   dict(command='BEFRIEND',winding=0,other=n),dict(command='MOVE',winding=n,x=2.34567891,y=-3.45678912),
   dict(command='MOVETO',winding=1 if n==2 else n,x=80.123456789,y=90.987654321),
   dict(command='UNFRIEND',winding=0,other=n),dict(command='MOVE',winding=n,x=-.123456789,y=.987654321),
   dict(command='RENAME',winding=n+1,name='c2_renamed'),dict(command='BEFRIEND',winding=n,other=n),
   dict(command='MOVE',winding=n,x=.123456789,y=.234567891),dict(command='MOVETO',winding=n,x=40.123456789,y=50.987654321),
   dict(command='UNFRIEND',winding=n,other=n),dict(command='COPY',winding=n+1,name='c3',metal='M2'),
   dict(command='COPY',winding=0,name='c4',metal='M1',x=123.456789),dict(command='RENAME',winding=0,name='source_new')]
  yield c
 # Rejected names/links keep the original geometry. The duplicate-destination
 # COPY also retains the native incomplete descriptor left by its rejection.
 base=copy.deepcopy(next(c for c in spatial_jobs()if c['label']=='wire'))
 for label,operations in[
  ('rename-same',[dict(command='RENAME',winding=0,name='a')]),
  ('copy-same',[dict(command='COPY',winding=0,name='a')]),
  ('rename-used',[dict(command='COPY',winding=0,name='b'),dict(command='RENAME',winding=0,name='b')]),
  ('unfriend-wrong',[dict(command='COPY',winding=0,name='b'),dict(command='UNFRIEND',winding=0,other=1)]),
  ('copy-used',[dict(command='COPY',winding=0,name='b'),dict(command='COPY',winding=0,name='b')])]:
  c=copy.deepcopy(base);c['label']=label;c['operations']=operations;yield c

def command(op,names):
 cmd=op['command'];name=names[op['winding']]
 if cmd in('COPY','RENAME'):
  result=f'{cmd} {name} {op["name"]}'
  if cmd=='COPY'and'metal'in op:
   result+=' '+op['metal']
   if'x'in op:result+=' '+format(op['x'],'.17g')
   if'y'in op:result+=' '+format(op['y'],'.17g')
  return result+'\n'
 if cmd in('BEFRIEND','UNFRIEND'):return f'{cmd} {name} {names[op["other"]]}\n'
 return spatial_command(op,names)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args();ref=a.reference.resolve();original=ref/'run/asitic.linux.2.2'
 for path,want in((original,ORIGINAL_SHA256),(ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
  if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
 cases=[];parents={}
 with tempfile.TemporaryDirectory(prefix='pyasitic-original-copy-links-')as directory:
  for c in jobs():
   parents[c['parent']]=hashlib.sha256((ROOT/'tests/fixtures'/f'{c["parent"]}.json').read_bytes()).hexdigest();names=c['names'].copy();script=c['creation']+f'GEOM {names[0]}\n'
   for op in c['operations']:
    script+=command(op,names);new=op.get('name','').upper()
    if op['command']=='COPY'and new not in names:names.append(new)
    elif op['command']=='RENAME'and new not in names:names[op['winding']]=new
    script+=f'GEOM {names[0]}\n'
   work=Path(directory)/str(len(cases));work.mkdir()
   for name,value in(('process.tek',c['technology']),('input.asit',script),('answers.txt',c['stdin']),('capture.gdb',COMMANDS)):(work/name).write_text(value)
   run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
   if run.returncode or not(work/'spatial.json').exists()or'Python Exception'in run.stderr:raise RuntimeError(c['label']+run.stdout[-1500:]+run.stderr[-1000:])
   observed=json.loads((work/'spatial.json').read_text())
   if len(observed['states'])!=len(c['operations'])+1:raise RuntimeError('Incomplete original history '+c['label'])
   cases.append(dict(c,script=script,stdout=run.stdout,stderr=run.stderr,**observed));print(c['label'],len(observed['states']),'states; signal',observed['signal'],flush=True)
 result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents=parents,gdb_commands=COMMANDS,reference='Unchanged original full COPY/RENAME/BEFRIEND/UNFRIEND and follow-up spatial command histories, all twelve generators. Read-only GEOM-entry observers retain every linked descriptor, name, origin, friend pointer, ordered XYZ/material/width/thickness/via store and control word. Native name/link rejections and the incomplete descriptor left by duplicate-COPY rejection retained. No numerical or allocator replacement.',cases=cases)
 with gzip.GzipFile(str(ROOT/'tests/fixtures/copy_links_original.json.gz'),'wb',mtime=0)as out:out.write((json.dumps(result,separators=(',',':'),allow_nan=False)+'\n').encode())

if __name__=='__main__':main()
