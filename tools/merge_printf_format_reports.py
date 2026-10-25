"""Losslessly merge every disjoint required formatter shard; no difference filters."""
import argparse,collections,json
from pathlib import Path


def merge(parts):
    merged={}
    for scope in('prefix','complete'):
        reports=[p[scope]for p in parts];total=reports[0]['total_cases'];shards=reports[0]['shards'];by_index={};terminals=collections.Counter()
        if len(reports)!=shards or sorted(p['shard']for p in reports)!=list(range(1,shards+1)):raise ValueError('Missing or repeated formatter shard')
        for r in reports:
            if r['scope']!=scope or r['total_cases']!=total or r['shards']!=shards:raise ValueError('Inconsistent formatter shard metadata')
            if r['case_indices']!=list(range(r['shard']-1,total,shards))or r['cases']!=len(r['results'])or len(r['case_indices'])!=len(r['results']):raise ValueError('Invalid formatter case partition')
            for index,result in zip(r['case_indices'],r['results']):
                if index in by_index:raise ValueError('Repeated formatter case')
                by_index[index]=result
            terminals.update(r['native_terminal_counts'])
        if sorted(by_index)!=list(range(total)):raise ValueError('Missing formatter cases')
        result=dict(scope=scope,total_cases=total,shard=1,shards=1,case_indices=list(range(total)),cases=total,cases_without_calls=sum(r['cases_without_calls']for r in reports),native_terminal_counts=dict(terminals),results=[by_index[i]for i in range(total)])
        for key in('calls_required','calls_checked','words_checked','registers_checked','fp_bytes_checked','children_checked','child_registers_checked','differences'):result[key]=sum(r[key]for r in reports)
        if result['differences']!=sum(len(r['differences'])for r in result['results']):raise ValueError('Difference count does not retain every target')
        merged[scope]=result
    return merged


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('parts',type=Path,nargs='+');p.add_argument('--output',type=Path,required=True);args=p.parse_args();report=merge([json.loads(p.read_text())for p in args.parts]);args.output.write_text(json.dumps(report,indent=2)+'\n')
    for scope,r in report.items():print(scope,{k:v for k,v in r.items()if k not in('results','case_indices')})


if __name__=='__main__':main()
