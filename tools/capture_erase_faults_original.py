"""Retain the original repeated-descriptor ERASE fault without allocator changes."""
import copy
from capture_phase_erase_original import main,generators

def jobs():
 c=copy.deepcopy(next(c for c in generators()if c['label']=='wire'));c['label']='repeated-descriptor';c['operations']=[dict(command='ERASE',windings=[0,0])];yield c
if __name__=='__main__':
 main(output_name='erase_faults_original',job_source=jobs,description='Unchanged original ERASE A A resolves the same descriptor twice and faults during removal. WHO-entry scene before the operation and terminal signal retained, with no allocator or numerical replacements.')
