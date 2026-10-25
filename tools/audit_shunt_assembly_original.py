"""Observe production JOINSHUNT filament groups, materials and upper assembly."""
import argparse,gzip,json,struct,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic import solver
from reasitic.bridge import handle
from audit_unjoin_assembly_original import compare as compare_upper


def compare(case):
    differences=[];counts={};geometry=[];assemblies=[]
    build=solver._filament_geometry;assemble=solver.assemble_impedance
    def observe_geometry(shape,technology,width,thickness,maximum,limit):
        result=build(shape,technology,width,thickness,maximum,limit)
        parents=[s for s in shape.segments if s.metal<len(technology.metals)]
        sizes=[solver.filament_counts(s,width,thickness,maximum)for parent in parents for s in(parent,*parent.secondary)]
        geometry.append((result,[len(s.secondary)for s in parents],sizes))
        return result
    def observe_assembly(wires,materials,pairs,frequency):
        result=assemble(wires,materials,pairs,frequency)
        assemblies.append((wires,materials,result));return result
    def check(kind,actual,expected,where):
        counts[kind]=counts.get(kind,0)+1
        if actual!=expected:differences.append(dict(kind=kind,where=where,actual=actual,original=expected))
    with patch.object(solver,'_filament_geometry',observe_geometry),patch.object(solver,'assemble_impedance',observe_assembly):handle(case['request'])
    check('geometry-calls',len(geometry),1,'prepare_impedance');check('assembly-calls',len(assemblies),1,'prepare_impedance')
    if geometry:
        (filaments,groups),extra,sizes=geometry[0]
        check('group-count',len(groups),case['group_count'],'groups');check('extra-segments',extra,case['extra_segments'],'groups')
        check('width-counts',[s[0]for s in sizes],case['width_counts'],'segments');check('thickness-counts',[s[1]for s in sizes],case['thickness_counts'],'segments')
        offset=segment=0
        for i,group in enumerate(groups):
            extent=sum(a*b for a,b in zip(case['width_counts'][segment:segment+extra[i]+1],case['thickness_counts'][segment:segment+extra[i]+1]))
            check('filament-group',group,list(range(offset,offset+extent)),i);offset+=extent;segment+=extra[i]+1
    if assemblies:
        wires,materials,matrix=assemblies[0];check('filament-count',len(wires),case['n'],'assembly')
        for i,(wire,material,native)in enumerate(zip(wires,materials,case['records'])):
            check('filament-input',struct.pack('<8d',*wire).hex(),native['wire_bits'],i)
            check('filament-material',struct.pack('<2d',*material).hex(),struct.pack('<2d',native['sheet_resistance'],native['thickness_count']).hex(),i)
        target=bytes.fromhex(case['upper_bits']);at=0
        for j in range(case['n']):
            for i in range(j+1):
                check('production-upper',struct.pack('<2d',matrix[i][j].real,matrix[i][j].imag).hex(),target[at:at+16].hex(),[i,j]);at+=16
    return dict(label=case['label'],counts=counts,differences=differences)


def run(fixture):
    results=[]
    for case in fixture['cases']:
        upper=compare_upper(case);production=compare(case)
        results.append(dict(label=case['label'],upper=upper,production=production))
    return dict(cases=len(results),upper_entries_checked=sum(r['upper']['upper_entries_checked']for r in results),differences=sum(len(r[k]['differences'])for r in results for k in('upper','production')),results=results)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
    report=run(json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_assembly_original.json.gz').read_bytes())))
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    for case in report['results']:print(case['label'],len(case['upper']['differences']),len(case['production']['differences']),'upper / production differences')
    print({k:v for k,v in report.items()if k!='results'});raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()
