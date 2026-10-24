"""Strict native GEOM/METALAREA stores, including recorded nonfinite payload words."""
import collections,gzip,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from reasitic.geometry_metrics import _evaluate
from test_geometry_metrics_original import bits,raw


def main():
    root=ROOT/'tests/fixtures';counts=collections.Counter();differences=collections.Counter();details=[]
    cli=json.loads(gzip.decompress((root/'geometry_metrics_original.json.gz').read_bytes()))['cases'];primitive=json.loads((root/'geometry_primitives_original.json').read_text())['cases'];jobs=[]
    for c in cli:
        if not c['geom']:continue
        jobs.append((c['label'],c['geom'][0]['records'],[c['reports'][0]['length_bits'],c['reports'][0]['area_bits'],c['reports'][1]['area_bits'],c['metalarea'][0]['extended_bits']]))
    jobs.extend((c['label'],c['records'],[c['length_bits'],c['area_bits'],c['metal_area_bits'],c['metal_area_extended_bits']])for c in primitive)
    for label,records,want in jobs:
        got=_evaluate(b''.join(bytes.fromhex(p)for p in records));actual=[bits(v)for v in got]+[raw(got[2])]
        for kind,a,b in zip(('length_F64','area_F64','metal_area_F64','metal_area_R80'),actual,want):
            counts[kind]+=1
            if a!=b:differences[kind]+=1;details.append((label,kind,a,b))
    print('Strict original geometry metrics:',dict(counts));print('Differences:',dict(differences))
    for detail in details:print(detail)
    raise SystemExit(bool(differences))


if __name__=='__main__':main()
