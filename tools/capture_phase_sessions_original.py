"""Full original models after PHASE edits, including reversed mutual coupling."""
import copy,gzip,json
from capture_copy_sessions_original import ROOT,main,jobs as copy_jobs
from capture_phase_erase_original import command

def jobs():
 for label,parent,r,prefix,stdin,names in copy_jobs():
  r=copy.deepcopy(r);r['edits'].append(dict(command='PHASE',winding=r['winding'],phase=1 if r['kind']=='via'else -1))
  yield label,parent,r,prefix,stdin,names
 parent=ROOT/'tests/fixtures/paired_interactive_bounds_sessions_original.json.gz';c=json.loads(gzip.decompress(parent.read_bytes()))['cases'][2];r=copy.deepcopy(c['request']);r.update(winding=0,edits=[dict(command='PHASE',winding=0,phase=-1)])
 yield 'transformer/negative-primary',parent,r,c['script'].split('CALCTRANS',1)[0],c['stdin'],['A','B']

if __name__=='__main__':
 main(output_name='phase_sessions_original',job_source=jobs,command_source=command,description='Unchanged original copied WIRE/BALUN/VIA and TRANS followed by PHASE and full Pi2/CALCTRANS/2PORT. Six complete selected models, including reversed primary coupling and the native zero-phase BALUN no-op, plus the native nonfinite converted-VIA CAP reference. Read-only completed geometry/model/scattering/resonance/node observers; nonnumerical sprintf observer. Every selected outcome retained.')
