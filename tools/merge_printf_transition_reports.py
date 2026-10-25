"""Merge all disjoint printf-continuation shards without accepting differences."""
import argparse,collections,json
from pathlib import Path
from audit_printf_transition_original import COUNTERS


def merge(reports):
    total=reports[0]['total_cases'];shards=reports[0]['shards'];results={};terminals=collections.Counter()
    if len(reports)!=shards or sorted(r['shard']for r in reports)!=list(range(1,shards+1)):raise ValueError('Missing or repeated printf-continuation shard')
    for r in reports:
        indices=list(range(r['shard']-1,total,shards))
        if r['total_cases']!=total or r['shards']!=shards or r['case_indices']!=indices or len(indices)!=len(r['results'])or r['cases']!=len(indices):raise ValueError('Invalid printf-continuation partition')
        for i,c in zip(indices,r['results']):
            if i in results:raise ValueError('Repeated printf-continuation case')
            results[i]=c
        terminals.update(r['native_terminal_counts'])
    if sorted(results)!=list(range(total)):raise ValueError('Missing printf-continuation case')
    result=dict(total_cases=total,shard=1,shards=1,case_indices=list(range(total)),cases=total,native_terminal_counts=dict(terminals),results=[results[i]for i in range(total)])
    for key in(*COUNTERS,'differences'):result[key]=sum(r[key]for r in reports)
    if result['differences']!=sum(len(r['differences'])for r in result['results']):raise ValueError('Printf-continuation difference count differs')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('parts',nargs='+',type=Path);p.add_argument('--output',type=Path,required=True);args=p.parse_args();report=merge([json.loads(p.read_text())for p in args.parts]);args.output.write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items()if k not in('results','case_indices')})


if __name__=='__main__':main()
