"""Full original electrical models after deletion and recycled friend links."""
import copy
from capture_copy_sessions_original import main,jobs as copied_jobs
from capture_phase_erase_original import command

def jobs():
 all_jobs=list(copied_jobs());wire=next(j for j in all_jobs if j[0]=='wire/pi2')
 for label,action in(('delete-middle/pi2','pi2'),('delete-source/calctrans','calctrans'),('rebound/pi2','pi2'),('rebound/calctrans','calctrans')):
  _,parent,r,prefix,stdin,names=copy.deepcopy(wire)
  if label.startswith('delete-middle'):r['edits'].append(dict(command='ERASE',windings=[1]));r.update(winding=1)
  elif label.startswith('delete-source'):r['edits'].append(dict(command='ERASE',windings=[0]));r.update(winding=1,first_winding=1,second_winding=0,termination_ohm=0)
  else:
   r.update(winding=2,first_winding=0,second_winding=2,termination_ohm=0,edits=[dict(command='COPY',winding=0,name='b'),dict(command='COPY',winding=0,name='c'),dict(command='BEFRIEND',winding=0,other=1),dict(command='BEFRIEND',winding=0,other=2),dict(command='ERASE',windings=[0]),dict(command='MOVE',winding=0,x=.125,y=-.25),dict(command='COPY',winding=1,name='d',metal='M2'),dict(command='MOVE',winding=0,x=1,y=2)])
   if action=='calctrans':r['winding']=0
  r['action']=action;yield label,parent,r,prefix,stdin,names
if __name__=='__main__':
 # Reuse the model/node observer, but CAP reference capture belongs to the
 # earlier VIA jobs and is not part of these wire-only ERASE sessions.
 main(output_name='erase_sessions_original',job_source=jobs,command_source=command,description='Unchanged original complete Pi2/CALCTRANS/2PORT after ERASE, including moved copies reached through a recycled stale friend pointer. Read-only full final geometry, raw model/Y/S/resonance/node observers and nonnumerical sprintf observer; every selected outcome retained.',capture_cap_reference=False)
