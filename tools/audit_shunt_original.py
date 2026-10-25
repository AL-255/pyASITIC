"""Strict defined geometry, group links and native phase words for JOINSHUNT."""
import argparse,gzip,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic import Technology
from reasitic.bridge import _shapes

KINDS=dict(square=0,polygon=1,wire=2,transformer=3,balun=5,transformer3d=10,via=14,symmetric_square=16,symmetric_polygon=17,capacitor=21,multimetal=21,joined=21,ring=22)


def compare(case):
    differences=[];words=records=links=phases=states=0
    for index,state in enumerate(case['states']):
        def check(kind,actual,expected,where):
            if actual!=expected:differences.append(dict(kind=kind,state=index,where=where,actual=actual,original=expected))
        try:shapes,partners=_shapes(dict(case['public'],edits=case['operations'][:index]),Technology.from_text(case['technology']),with_links=True)
        except (ValueError,NotImplementedError)as error:
            differences.append(dict(kind='shunt-runtime',state=index,reason=str(error)));continue
        native=list(reversed(state['shapes']));states+=1;check('shunt-names',[s.name for s in shapes],[s['name']for s in native],'scene');mapping={};pairs=[];primary_next={}
        for si,(shape,original)in enumerate(zip(shapes,native)):
            check('shunt-origin',struct.pack('<2d',*shape.origin).hex(),original['origin_bits'],si);check('shunt-kind',KINDS[shape.kind],original['native_kind'],si)
            check('shunt-phase',shape.electrical_phase,original['attributes'],si);phases+=1
            check('shunt-partner',shapes[partners[si]].name if partners[si]is not None else None,original['partner'],si);check('shunt-dangling',bool(shapes.dangling_partners[si]),original['dangling_partner'],si)
            check('shunt-primary-count',len(shape.segments),len(original['segments']),si)
            for ri,(record,target)in enumerate(zip(shape.segments,original['segments'])):
                primary_next[id(record)]=shape.segments[ri+1]if ri+1<len(shape.segments)else None;mapping[id(record)]=target['address'];pairs.append((record,target,[si,ri]))
                check('shunt-secondary-count',len(record.secondary),len(target['secondary']),[si,ri])
                for ci,(child,expected)in enumerate(zip(record.secondary,target['secondary'])):mapping[id(child)]=expected['address'];pairs.append((child,expected,[si,ri,ci]))
        for record,target,where in pairs:
            check('shunt-coordinates',struct.pack('<18d',*(v for p in record.points for v in p)).hex(),target['coordinates_bits'],where);words+=18;records+=1
            check('shunt-width',struct.pack('<d',record.width).hex(),target['width_bits'],where);check('shunt-metal',record.metal,target['metal'],where)
            if'thickness_bits'in target:
                for value,key in((record.thickness,'thickness_bits'),(record.width if record.primary_width is None else record.primary_width,'primary_width_bits'),(record.thickness if record.primary_thickness is None else record.primary_thickness,'primary_thickness_bits')):check('shunt-'+key,struct.pack('<d',value).hex(),target[key],where)
            else:check('shunt-via-counts',[record.nx,record.ny],[target['nx'],target['ny']],where)
            nxt=primary_next.get(id(record),getattr(record,'_native_next',None));group=record.secondary[0]if record.secondary else getattr(record,'_native_group_next',None)
            for key,value in(('next_address',nxt),('group_address',group)):
                actual=0 if value is None else mapping.get(id(value),'unowned-produced-record');check('shunt-'+key,actual,target[key],where);links+=1
    return dict(label=case['label'],states_checked=states,records_checked=records,coordinate_words_checked=words,links_checked=links,phase_words_checked=phases,differences=differences)


def run(fixture):
    results=[compare(c)for c in fixture['cases']];report=dict(cases=len(results),differences=sum(len(c['differences'])for c in results),results=results)
    for key in('states_checked','records_checked','coordinate_words_checked','links_checked','phase_words_checked'):report[key]=sum(c[key]for c in results)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/shunt_original.json.gz');parser.add_argument('--output',type=Path);args=parser.parse_args();report=run(json.loads(gzip.decompress(args.fixture.read_bytes())))
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    for case in report['results']:print(case['label'],len(case['differences']),'differences')
    print({k:v for k,v in report.items()if k!='results'});raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()
