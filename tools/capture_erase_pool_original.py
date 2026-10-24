"""Original descriptor reuse after multi-ERASE with every stale incoming link."""
import copy
from capture_phase_erase_original import main,generators

def jobs():
 base=next(c for c in generators()if c['label']=='wire')
 for n in(1,2,7,8,9,10,15):
  c=copy.deepcopy(base);c['label']=f'pool/{n}';ops=[]
  for i in range(n):ops.append(dict(command='COPY',winding=0,name=f'r{i}'))
  for i in range(n):ops.extend([dict(command='COPY',winding=0,name=f'b{i}'),dict(command='BEFRIEND',winding=i+1,other=n+i+1),dict(command='BEFRIEND',winding=i+1,other=i+1)])
  ops.append(dict(command='ERASE',windings=list(range(1,n+1)),**({'expect_rejection':True}if n>10 else{})))
  for i in range(n):ops.append(dict(command='COPY',winding=0,name=f'd{i}'))
  for i in range(n):ops.append(dict(command='MOVE',winding=(n if n>10 else 0)+i+1,x=.125,y=-.25))
  c['operations']=ops;yield c
 for kind,source,old_source in(('polygon',0,0),('balun',0,0),('balun',1,0),('balun',0,1)):
  c=copy.deepcopy(next(c for c in generators()if c['label']==kind));n=8;base_count=len(c['names']);c['label']=f'pool/{kind}/source{source}/from{old_source}/8';ops=[]
  for i in range(n):ops.append(dict(command='COPY',winding=old_source,name=f'r{i}'))
  for i in range(n):ops.extend([dict(command='COPY',winding=old_source,name=f'b{i}'),dict(command='BEFRIEND',winding=base_count+i,other=base_count+n+i),dict(command='BEFRIEND',winding=base_count+i,other=base_count+i)])
  ops.append(dict(command='ERASE',windings=list(range(base_count,base_count+n))))
  for i in range(n):ops.append(dict(command='COPY',winding=source,name=f'd{i}'))
  for i in range(n):ops.append(dict(command='MOVE',winding=base_count+i,x=.125,y=-.25))
  c['operations']=ops;yield c
if __name__=='__main__':
 main(output_name='erase_pool_original',job_source=jobs,description='Unchanged original descriptor reuse after 1/2/7/8/9/10/15 ERASE arguments and polygon/balun same-size, smaller and larger copies, preserving every stale incoming pointer. WHO-entry observer retains complete scenes, raw descriptors, phase/material geometry, dangling links, reallocated identities and subsequent moves. All selected outcomes retained, including native faults.')
