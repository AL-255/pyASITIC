"""Complete original model sessions after series joins and reused friend links."""
import argparse,copy,gzip,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from capture_copy_sessions_original import main,jobs as earlier_jobs
from capture_join_original import command,update_names,generators
ROOT=Path(__file__).resolve().parents[1]

def initial_jobs():
 bases=[c for c in generators()if '/edges/'not in c['label']]
 for label,kind,action in [('wire/pi2','wire','pi2'),('square/pi2','square','pi2'),('recycled-transformer/pi2','transformer','pi2'),('recycled-transformer/calctrans','transformer','calctrans')]:
  c=copy.deepcopy(next(c for c in bases if c['label']==kind));r=dict(c['public'],action=action,technology=c['technology'],frequency_hz=1.23456789e9,frequency_ghz=1.23456789,eddy=False,mesh=dict(length_cell=1000,width_cell=1000,thickness_cell=1000,capacitance_length_cell=1000,capacitance_width_cell=1000),winding=0)
  if kind=='transformer':r['edits']=[dict(command='JOIN',winding=0,others=[1]),dict(command='COPY',winding=0,name='d',metal='M2',x=40,y=70),dict(command='MOVE',winding=0,x=.125,y=-.25)]
  else:r['edits']=[dict(command='COPY',winding=0,name='c',metal='M2',x=40,y=70),dict(command='PHASE',winding=1,phase=-1),dict(command='JOIN',winding=0,others=[1]),dict(command='MOVEX',winding=0,x=.125)]
  if action=='calctrans':r.update(first_winding=0,second_winding=1,termination_ohm=0)
  prefix='CELL 1000 1000 1000\nCCELL 1000 1000\nEDDY OFF\n'+c['creation']
  yield label,ROOT/'tests/fixtures'/f"{c['parent']}.json",r,prefix,c['stdin'],c['names']


def jobs():
 yield from initial_jobs()
 wire=next(j for j in earlier_jobs()if j[0]=='wire/pi2')
 _,parent,r,prefix,stdin,names=copy.deepcopy(wire)
 r.update(winding=0,edits=[dict(command='COPY',winding=0,name='c',metal='M2'),dict(command='PHASE',winding=1,phase=-1),dict(command='JOIN',winding=0,others=[1]),dict(command='MOVEX',winding=0,x=.125)])
 yield 'finite-wire/pi2',parent,r,prefix,stdin,names
 parent=ROOT/'tests/fixtures/square_sessions_original.json';c=json.loads(parent.read_text())['cases'][0];r=copy.deepcopy(c['request']);r.update(winding=0,edits=[dict(command='COPY',winding=0,name='c',metal='M2'),dict(command='PHASE',winding=1,phase=-1),dict(command='JOIN',winding=0,others=[1]),dict(command='MOVEX',winding=0,x=.125)])
 yield 'finite-square/pi2',parent,r,c['script'].split('PI2',1)[0],c.get('stdin','quit\n'),['A']
 paired=next(j for j in earlier_jobs()if j[0]=='balun/calctrans')
 for action in('pi2','calctrans'):
  _,parent,r,prefix,stdin,names=copy.deepcopy(paired)
  r.update(action=action,winding=0,first_winding=0,second_winding=1,termination_ohm=0,edits=[dict(command='JOIN',winding=0,others=[1]),dict(command='COPY',winding=0,name='d',metal='M2',x=40,y=40),dict(command='MOVE',winding=0,x=.125,y=-.25)])
  yield 'finite-balun/'+action,parent,r,prefix,stdin,names

def capture_plain(*,output_name='join_plain_outcomes_original',job_source=jobs,command_source=command,names_source=update_names,description=None):
 from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
 p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args();original=a.reference/'run/asitic.linux.2.2'
 for path,digest in((original,ORIGINAL_SHA256),(a.reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
  assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
 accepted=[];results=[];parents={}
 with tempfile.TemporaryDirectory(prefix='pyasitic-join-plain-')as directory:
  for job in job_source():
   label,parent,r,prefix,stdin,names=copy.deepcopy(job);parents[parent.name]=hashlib.sha256(parent.read_bytes()).hexdigest();script=prefix
   for op in r['edits']:script+=command_source(op,names);names_source(names,op)
   first=names[r['winding']];freq=format(r['frequency_ghz'],'.17g');script+=f'GEOM {first}\n'
   if r['action']=='calctrans':
    second=names[r['second_winding']];script+=f'CALCTRANS {first} {second} {freq}\n2PORTTRANS {first} {second} {freq} {freq} 1 S RECT s.out\n'
   else:script+=f'PI2 {first} {freq}\n2PORT {first} {freq} {freq} 1 S RECT SLOW s.out\n'
   work=Path(directory)/str(len(results));work.mkdir();(work/'process.tek').write_text(r['technology']);(work/'input.asit').write_text(script)
   run=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),input=stdin,capture_output=True,text=True,start_new_session=True,timeout=120)
   successful=run.returncode==0 and(work/'s.out').exists()and'Could not generate capacitance matrix'not in run.stdout
   results.append(dict(label=label,request=r,script=script,stdin=stdin,returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,produced_model=successful));print(label,'unobserved model:',successful,flush=True)
   if successful:accepted.append(copy.deepcopy(job))
 result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents=parents,reference=description or'Every selected JOIN model request executed by the unchanged binary without GDB, preload taps, or replacements. Failed model attempts remain here with their complete scripts/requests/outputs; successful cases additionally receive read-only raw model observers.',cases=results)
 with gzip.GzipFile(str(ROOT/'tests/fixtures'/f'{output_name}.json.gz'),'wb',mtime=0)as f:f.write((json.dumps(result,separators=(',',':'))+'\n').encode())
 return accepted

if __name__=='__main__':
 accepted=capture_plain()
 main(output_name='join_sessions_original',job_source=lambda:iter(accepted),command_source=command,names_source=update_names,capture_cap_reference=False,description='Unchanged original complete JOIN/Pi2/CALCTRANS/2PORT histories, including translated mixed-metal wires, joined square segments/vias, paired-descriptor deletion and a copied winding reached through a reused stale friend address. Read-only final geometry, raw model/Y/S/resonance/node observers and nonnumerical sprintf observer; all selected outcomes retained.')
