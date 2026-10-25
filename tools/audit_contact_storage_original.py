"""Compare source-generated prepared and numbered contact bytes exactly."""
import argparse,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.contact_storage import records,write_prepared,number_contacts,number_groups
from reasitic.memory import Memory,UnknownMemory
import audit_cap_prelude_original as prelude
from audit_shared_heap_original import ported_inductance_geometry,ported_reference


def ported_records(case):
    from reasitic.bridge import _mesh,_shapes
    shape,technology=ported_inductance_geometry(case);request=case['request'];mesh=_mesh(request,technology)
    name=shape.name
    if request['action']=='calctrans':
        # later_analysis.cpp copies the first discretized winding with a null
        # requested name. composite_geometry.cpp first tries source + '_'.
        name=f'{name}_'
        if name in {s.name for s in _shapes(request,technology)}:
            raise NotImplementedError('Native automatic-copy name collision needs its random-state history')
    chip=technology.chip
    result=records(shape,technology,int(chip['fftx']),int(chip['ffty']),float(chip['chipx']),float(chip['chipy']),
                   mesh['capacitance_length_cell'],mesh['capacitance_width_cell'],name=name)
    ground=ported_reference(case,shape,technology)
    if ground.name!=shape.name:result+=records(ground,technology,int(chip['fftx']),int(chip['ffty']),float(chip['chipx']),float(chip['chipy']),mesh['capacitance_length_cell'],mesh['capacitance_width_cell'])
    return result


def compare(case):
    prefix,heap,addresses=prelude.compare(case,return_state=True)
    result=dict(label=case['label'],cache_mode=case['cache_mode'],differences=list(prefix['differences']),
                objects_checked=0,bytes_checked=0,unknown_bytes=0,stages=[])
    if result['differences']:return result
    groups=ported_records(case);memory=Memory(heap.address_space);write_prepared(memory,groups,addresses)
    for state in case['contact_storage']:
        numbered=state['label']=='numbered'
        if numbered:number_contacts(memory,groups,addresses);number_groups(memory,groups,addresses)
        stage=dict(label=state['label'],objects_checked=0,bytes_checked=0,unknown_bytes=0)
        if state['head']!=addresses['contact_group.0']:result['differences'].append(dict(kind='head',stage=state['label']))
        if len(state['groups'])!=len(groups):result['differences'].append(dict(kind='group-count',stage=state['label']));break
        def check(name,observed,size,ranges,unknown):
            address=addresses[name];raw=bytes.fromhex(observed['data'])
            if observed['address']!=address:result['differences'].append(dict(kind='address',stage=state['label'],name=name,actual=address,original=observed['address']))
            assert len(raw)==size
            for offset,count in ranges:
                actual=memory.read(address+offset,count);expected=raw[offset:offset+count];stage['bytes_checked']+=count
                if actual!=expected:result['differences'].append(dict(kind='bytes',stage=state['label'],name=name,offset=offset,actual=actual.hex(),original=expected.hex()))
            for offset,count in unknown:
                for byte in range(count):
                    try:memory.read(address+offset+byte,1)
                    except UnknownMemory:stage['unknown_bytes']+=1
                    else:result['differences'].append(dict(kind='unexpected-initialization',stage=state['label'],name=name,offset=offset+byte))
            stage['objects_checked']+=1
        for i,(group,original)in enumerate(zip(groups,state['groups'])):
            ranges=[(0,len(group.name)),(80,44),(128,8)];unknown=[(len(group.name),80-len(group.name))]
            if numbered:ranges.append((124,4))
            else:unknown.append((124,4))
            check(f'contact_group.{i}',original,136,ranges,unknown)
            if len(original['contacts'])!=len(group.contacts):result['differences'].append(dict(kind='contact-count',stage=state['label'],group=i));continue
            for j,contact in enumerate(original['contacts']):
                check(f'contact.{i}.{j}',contact,60,[(0,60)]if numbered else[(0,52),(56,4)],[]if numbered else[(52,4)])
        result['stages'].append(stage)
        for key in ('objects_checked','bytes_checked','unknown_bytes'):result[key]+=stage[key]
    if [stage['label']for stage in case['contact_storage']]!=['prepared','numbered']:
        result['differences'].append(dict(kind='stage-order',actual=[stage['label']for stage in case['contact_storage']]))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/contact_storage_original.json.gz');parser.add_argument('--output',type=Path);options=parser.parse_args()
    fixture=json.loads(gzip.decompress(options.fixture.read_bytes()));results=[compare(case)for case in fixture['cases']]
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('objects_checked','bytes_checked','unknown_bytes'):report[key]=sum(r[key]for r in results)
    if options.output:options.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items()if key!='results'},separators=(',',':')))
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()
