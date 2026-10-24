"""Original PHASE predicates, endpoint stores, copying and zero-state histories."""
import copy,json,re
from capture_phase_erase_original import main,ROOT,generators

def bases():
 yield from generators()
 for source in generators():
  if source['label']not in('polygon','ring'):continue
  c=copy.deepcopy(source);c['label']+='-keyword-zero';c['public']['parameters']['phase']=0
  c['creation']=re.sub(r'PHASE=[^:\n]*','PHASE=0',c['creation'])if'PHASE='in c['creation']else c['creation'].rstrip('\n')+':PHASE=0\n'
  yield c
  c=copy.deepcopy(source);value=-3 if source['label']=='polygon'else 2;c['label']+='-keyword-integer';c['public']['parameters']['phase']=value
  c['creation']=re.sub(r'PHASE=[^:\n]*',f'PHASE={value}',c['creation'])if'PHASE='in c['creation']else c['creation'].rstrip('\n')+f':PHASE={value}\n'
  yield c
 for parent,kind,label,predicate in [
  ('primitive_original','capacitor','capacitor-keyword',lambda c:c['kind']=='capacitor'and c.get('native_keyword')),
  ('transformer3d_original','transformer3d','transformer3d-negative',lambda c:c['parameters'].get('phase')==-1),
  ('symmetric_interactive_original','symmetric_square','symmetric_square-interactive',lambda c:c['kind']=='symmetric_square'),
  ('symmetric_interactive_original','symmetric_polygon','symmetric_polygon-interactive',lambda c:c['kind']=='symmetric_polygon')]:
  f=json.loads((ROOT/'tests/fixtures'/f'{parent}.json').read_text());i,c=next((i,c)for i,c in enumerate(f['cases'])if predicate(c));names=[w['name']for w in c['windings']]if'windings'in c else[c['parameters']['name']]
  public=dict(kind=kind,parameters=c['parameters'],**{k:c[k]for k in('native_keyword','native_interactive')if k in c})
  yield dict(label=label,parent=parent,parent_index=i,public=public,technology=c.get('technology',f.get('technology')),creation=c['script'],stdin=c.get('stdin','quit\n')+('quit\n'if'quit'not in c.get('stdin','quit')else''),names=names)

def phase_jobs():
 for c in bases():
  if '/edges/'in c['label']:continue
  c=copy.deepcopy(c);n=len(c['names']);c['operations']=[dict(command='PHASE',winding=0,phase=-1),dict(command='PHASE',winding=0,phase=-1),dict(command='COPY',winding=0,name='neg'),dict(command='PHASE',winding=n,phase=2),dict(command='FLIP',winding=0),dict(command='PHASE',winding=0,phase=1),dict(command='PHASE',winding=0,phase=-2),dict(command='ROTATE',winding=0,angle=0),dict(command='PHASE',winding=0,phase=0),dict(command='PHASE',winding=0,phase=-1),dict(command='PHASE',winding=n,phase=-2147483648),dict(command='PHASE',winding=n,phase=2147483647),dict(command='PHASE',winding=n,phase=0),dict(command='PHASE',winding=n,phase=-2),dict(command='PHASE',winding=n,phase=1)];yield c

if __name__=='__main__':
 main(output_name='phase_original',job_source=phase_jobs,description='Unchanged original PHASE histories for all twelve generators, repeated/sign/zero/int32 phases, endpoint versus segment-list reversal, rotations and inherited copied phase state. Read-only WHO-entry snapshots preserve every selected outcome. The standalone interactive CAP creator leaves an uninitialized positive phase word; its initial sign is retained as an opaque predicate, not a fabricated numeric address.')
