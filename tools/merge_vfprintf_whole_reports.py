"""Merge every disjoint whole-parent shard without filtering differences."""
import argparse,collections,json
from pathlib import Path


def merge(reports):
    total=reports[0]['total_cases'];shards=reports[0]['shards'];results={};terminals=collections.Counter()
    if len(reports)!=shards or sorted(r['shard']for r in reports)!=list(range(1,shards+1)):raise ValueError('Missing or repeated whole-parent shard')
    for r in reports:
        if r['total_cases']!=total or r['shards']!=shards or r['case_indices']!=list(range(r['shard']-1,total,shards))or len(r['case_indices'])!=len(r['results'])or r['cases']!=len(r['results']):raise ValueError('Invalid whole-parent partition')
        for index,result in zip(r['case_indices'],r['results']):
            if index in results:raise ValueError('Repeated whole-parent case')
            results[index]=result
        terminals.update(r['native_terminal_counts'])
    if sorted(results)!=list(range(total)):raise ValueError('Missing whole-parent case')
    result=dict(total_cases=total,shard=1,shards=1,case_indices=list(range(total)),cases=total,cases_without_calls=sum(r['cases_without_calls']for r in reports),native_terminal_counts=dict(terminals),results=[results[i]for i in range(total)])
    for key in('parent_calls_required','calls_checked','words_checked','registers_checked','fp_bytes_checked','children_checked','child_registers_checked','boundary_states_checked','boundary_words_checked','boundary_registers_checked','boundary_fp_bytes_checked','differences'):result[key]=sum(r[key]for r in reports)
    if result['differences']!=sum(len(r['differences'])for r in result['results']):raise ValueError('Whole-parent difference count differs')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('parts',type=Path,nargs='+');p.add_argument('--output',type=Path,required=True);args=p.parse_args();report=merge([json.loads(p.read_text())for p in args.parts]);args.output.write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items()if k not in('results','case_indices')})


if __name__=='__main__':main()
