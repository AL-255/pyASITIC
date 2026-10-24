"""Additional native longitudinal clone and large COPY-name histories."""
import copy,hashlib
import capture_geometry_setup_original as capture


def jobs():
    base=list(capture.arena.lifetime.jobs())
    for cap,length in ((1000,37.5),(1,1000),(73.5,37.5)):
        job=copy.deepcopy(base[0]);job['label']=f'clone/subdivision/{cap}/{length}';job['variant']='longitudinal'
        job['request']['mesh'].update(length_cell=length,capacitance_length_cell=cap)
        job['script']=job['script'].replace('CELL 1000 1000 1000',f'CELL {length} 1000 1000').replace('CCELL 1000 1000',f'CCELL {cap} 1000')
        yield job
    job=copy.deepcopy(base[-1]);job['label']='calctrans/subdivision';job['variant']='longitudinal'
    job['request']['mesh'].update(length_cell=20,capacitance_length_cell=17)
    job['script']=job['script'].replace('CELL 1000 1000 1000','CELL 20 1000 1000').replace('CCELL 1000 1000','CCELL 17 1000')
    yield job
    # Length 63 fits the descriptor. Appending '_' crosses the string's
    # 64-byte capacity and requires a 144-byte libc allocation, not a pool hit.
    name='L'*63;job=copy.deepcopy(base[0]);job['label']='calctrans/large-copy-name';job['variant']='large-name'
    request=job['request'];request.update(action='calctrans',first_winding=0,second_winding=2,termination_ohm=0)
    request['parameters']['name']=name
    request['edits'].append(dict(command='COPY',winding=0,name='B',metal='M4',x=8,y=8))
    prefix=job['script'].split('GEOM A\n',1)[0].replace('NAME=A:',f'NAME={name}:').replace('UNJOIN A ',f'UNJOIN {name} ')
    job['script']=prefix+f'COPY {name} B M4 8 8\nGEOM {name}\nCALCTRANS {name} B .25\n2PORTTRANS {name} B .25 .25 1 S RECT s.out\n'
    yield job


if __name__=='__main__':
    parent=capture.arena.lifetime.ROOT/'tests/fixtures/geometry_setup_original.json.gz'
    capture.arena.main(observer=capture.OBSERVER,fixture_name='geometry_setup_extended_original.json.gz',command_builder=capture.commands,job_factory=jobs,
                       extra_metadata=dict(geometry_setup_parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),geometry_setup_reference='Additional inputs preserve all original 130 observations in their parent. Native longitudinal splitting, asymmetric CAP/inductive clone lengths, coupled clone/COPY/JOIN subdivision and long default names. Initial whole heap and string-pool state are read-only component inputs; every final shape/segment byte and allocation is an independent output observation.'))
