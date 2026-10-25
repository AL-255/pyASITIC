"""Check the decimal digit component against all independent native requests.

Text-only validation is deliberately separate from the unfinished complete
formatter ABI. Native output bytes are targets; only declared earlier bits,
field controls, and rounding mode enter the source computation.
"""
import argparse,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.printf_float_digits import format_binary64,extract_double,limb
from capture_printf_integer_original import LIBC_SHA256


def run(probe):
    if probe['libc_sha256']!=LIBC_SHA256:raise ValueError('Decimal probe uses a different libc build')
    if probe['tzcnt_zero']!=32:raise ValueError('Decimal probe uses a different TZCNT zero result')
    if probe['extract_double_offset']!=0x51ed0:raise ValueError('Decimal probe uses a different extraction helper')
    differences=[];checked=extracted=0
    for i,case in enumerate(probe['cases']):
        request={k:case[k]for k in('word','spec','precision','width','flags','rounding')}
        if(request['word']>>52)&2047!=2047:
            sig,count,exponent,negative=extract_double(request['word']);extracted+=1
            actual=dict(count=count,exponent=exponent,negative=negative,limbs=[limb(sig,0),limb(sig,1),0xa5a5a5a5,0xa5a5a5a5])
            if actual!=case['extraction']:differences.append(dict(case=i,request=request,kind='extraction',actual=actual,original=case['extraction']))
        elif case['extraction']is not None:differences.append(dict(case=i,request=request,kind='unexpected_nonfinite_extraction'))
        try:actual=b'P:'+format_binary64(**request)+b':S'
        except (ValueError,NotImplementedError,IndexError)as error:differences.append(dict(case=i,request=request,kind='runtime',reason=str(error)));continue
        checked+=1
        if actual.hex()!=case['original']:differences.append(dict(case=i,request=request,kind='text',actual=actual.hex(),original=case['original']))
    return dict(cases_required=len(probe['cases']),cases_checked=checked,extractions_checked=extracted,differences=differences)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--probe',type=Path,default=ROOT/'tests/fixtures/printf_float_digits_original.json.gz');p.add_argument('--output',type=Path);args=p.parse_args()
    probe=json.loads(gzip.decompress(args.probe.read_bytes()));report=run(probe)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(report['cases_checked'],'/',report['cases_required'],'binary64 decimal cases,',len(report['differences']),'differences');raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()
