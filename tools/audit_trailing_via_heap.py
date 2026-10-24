"""Strict source-lifetime comparison; does not infer physical heap addresses."""
import argparse,collections,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.allocation_plan import combined_network_storage


def compare(case):
    differences=[];via=case['via'];node=case['node']
    if via is None:return [dict(kind='missing-via-boundary')]
    completed=node is not None
    if not completed and case['signal']not in(6,11):differences.append(dict(kind='unexplained-missing-node',signal=case['signal']))
    external={}
    for i,g in enumerate(case['contact_groups']):
        external[f'contact_group.{i}']=g['address']
        external.update((f'contact.{i}.{j}',address)for j,address in enumerate(g['contacts']))
    external['geometry.descriptor']=via['shape_address'];external.update((f'geometry.segment.{i}',address)for i,address in enumerate(via['segment_addresses']))
    n=via['matrix']['size'];f=case['matrices']['ind_full']['size'];plan=combined_network_storage([len(g['contacts'])for g in case['contact_groups']],n,f,len(via['indices']),clone_segments=len(via['segments']))
    observed=[e for e in case['events']if e['kind']in('allocate','free')]
    if completed and len(plan)!=len(observed)or not completed and len(observed)>len(plan):differences.append(dict(kind='event-count',actual=len(plan),original=len(observed)))
    addresses=external.copy();live={v:k for k,v in addresses.items()}
    for index,(expected,actual)in enumerate(zip(plan,observed)):
        if expected.action!=actual['kind']or expected.allocator!=actual['allocator']:
            differences.append(dict(kind='event',index=index,actual=expected.__dict__,original=actual));continue
        if expected.action=='allocate':
            if expected.size!=actual['request']:differences.append(dict(kind='request',index=index,name=expected.name,actual=expected.size,original=actual['request']))
            if actual['address']in live:differences.append(dict(kind='live-address-reallocated',index=index,name=expected.name,previous=live[actual['address']]))
            addresses[expected.name]=actual['address'];live[actual['address']]=expected.name
        else:
            if addresses.get(expected.name)!=actual['address']:differences.append(dict(kind='free-identity',index=index,name=expected.name,actual=addresses.get(expected.name),original=actual['address'],original_owner=live.get(actual['address'])))
            if expected.allocator=='scalar':
                size=max(16,(expected.size+4+15)//16*16)
                if actual['chunk_size']!=size:differences.append(dict(kind='scalar-chunk',index=index,name=expected.name,actual=size,original=actual['chunk_size']))
            live.pop(actual['address'],None)
    if completed and set(live.values())!={'cap.output','ind.output'}:differences.append(dict(kind='live-at-node',actual=sorted(live.values())))
    for name,descriptor in [('cap.output',case['matrices']['cap_output']),('ind.output',via['matrix'])]:
        if addresses.get(name)!=descriptor['data']:differences.append(dict(kind='output-owner',name=name,actual=addresses.get(name),original=descriptor['data']))
    return differences


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/trailing_via_heap_original.json.gz');p.add_argument('--output',type=Path);a=p.parse_args()
    f=json.loads(gzip.decompress(a.fixture.read_bytes()))
    for name,digest in f['parents'].items():assert hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest()==digest
    differences=[];outcomes=collections.Counter();aliases=collections.Counter();events=0;boundaries=collections.Counter()
    for c in f['cases']:
        mode=c.get('cache_mode','earlier-warm-observer');outcomes[mode+'/'+str(c['plain']['returncode'])]+=1
        for d in compare(c):differences.append(dict(label=c['label'],cache_mode=mode,**d))
        events+=sum(e['kind']in('allocate','free')for e in c['events'])
        boundaries[mode+('/node'if c['node']is not None else'/fault-prefix')]+=1
        if c['via']is None:continue
        n=c['via']['matrix']['size'];cap=c['matrices']['cap_output']['data']
        for cell in c['via']['cells']:
            if cell['index']<n:continue
            delta=cell['address']-cap;inside=0<=delta<16*n*n and delta%16==0
            aliases[mode+('/CAP'if inside else'/outside-CAP')]+=1
    report=dict(cases=len(f['cases']),allocation_free_events=events,boundaries=boundaries,outcomes=outcomes,targets=aliases,differences=differences)
    if a.output:a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report if len(differences)<5 else{k:v for k,v in report.items()if k!='differences'},separators=(',',':')))
    raise SystemExit(int(bool(differences)))


if __name__=='__main__':main()
