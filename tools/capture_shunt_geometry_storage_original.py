"""Original JOINSHUNT groups through clone/COPY/JOIN and CAP preparation."""
import copy,gzip,hashlib,json
from pathlib import Path
import capture_geometry_setup_original as capture
ROOT=Path(__file__).resolve().parents[1]


def jobs():
    parent=ROOT/'tests/fixtures/shunt_sessions_original.json.gz'
    cases=json.loads(gzip.decompress(parent.read_bytes()))['cases']
    for c in cases:
        yield dict(label=c['label'],parent=parent,request=copy.deepcopy(c['request']),script=c['script'],stdin=c['stdin'],variant='shunt-groups')
    square=next(c for c in cases if c['label']=='square/coarse')
    for label,length,cap in(('unequal-branch/refined',35,1000),('unequal-branch/asymmetric',1000,17)):
        request=copy.deepcopy(square['request']);request['parameters']['exit_metal']=-1
        request['mesh'].update(length_cell=length,capacitance_length_cell=cap)
        request['edits']=[dict(command='COPY',winding=0,name='c',metal='M2'),dict(command='UNJOIN',winding=1,index=1,name='tail'),dict(command='JOINSHUNT',winding=0,others=[1])]
        prefix=square['script'].split('COPY',1)[0].replace('EXIT=M3','EXIT=-1').replace('CELL 1000 1000 1000',f'CELL {length} 1000 1000').replace('CCELL 1000 1000',f'CCELL {cap} 1000')
        frequency=format(request['frequency_ghz'],'.17g')
        script=prefix+'COPY A c M2\nUNJOIN C 1 TAIL\nJOINSHUNT A C\nGEOM A\n'+f'PI2 A {frequency}\n2PORT A {frequency} {frequency} 1 S RECT SLOW s.out\n'
        yield dict(label=label,parent=parent,request=request,script=script,stdin=square['stdin'],variant='unequal-branch')


if __name__=='__main__':
    parent=ROOT/'tests/fixtures/shunt_sessions_original.json.gz'
    capture.arena.main(observer=capture.OBSERVER,fixture_name='shunt_geometry_storage_original.json.gz',command_builder=capture.commands,job_factory=jobs,
                       extra_metadata=dict(geometry_setup_parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),geometry_setup_reference='Every twelve-session JOINSHUNT model parent plus two independently specified unequal-length branch histories, each in cold and warm original cache states. The longer child controls common subdivision count; asymmetric cells exercise typed one-part cloning. Initial driver-entry whole heap, source scene including all secondary groups, string pool and allocator are component inputs. Later clone/COPY/JOIN descriptor/segment bytes, links, allocation/free order, string pool, allocator and CAP preparation are independent read-only observations. No native instruction, memory, register, allocation, affinity or result is replaced.'))
