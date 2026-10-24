"""Read-only helper/instruction trace for the remaining reversed COUPLING pair."""
import argparse,gzip,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from capture_mutual_command_traces_original import COMMANDS,ROOT,ORIGINAL_SHA256,LEGACY_SHA256


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);args=parser.parse_args();ref=args.reference.resolve();original=ref/'run/asitic.linux.2.2'
    for path,want in[(original,ORIGINAL_SHA256),(ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
    parent=ROOT/'tests/fixtures/coupling_original.json.gz';c=json.loads(gzip.decompress(parent.read_bytes()))['cases'][92];call=2;pair=1653;p=c['calls'][call]['pairs'][pair]
    target=sum(len(e['pairs'])for e in c['calls'][:call])+pair
    old="""while ordinal<target:
 gdb.execute('continue',to_string=True);assert reg('pc')==0x8061110;ordinal+=1"""
    new="""while True:
 assert reg('pc')==0x8061110
 if u32(reg('esp'))==0x804d113:
  if ordinal==target:break
  ordinal+=1
 gdb.execute('continue',to_string=True)"""
    assert old in COMMANDS;commands=COMMANDS.replace(old,new)
    points=json.loads((ROOT/'tests/fixtures/mutual_command_traces_original.json').read_text())['math_instruction_points'];points={int(k,16):v for k,v in points.items()}
    commands=commands.replace('TARGET',str(target)).replace('MATHPOINTS',repr(points))
    with tempfile.TemporaryDirectory(prefix='pyasitic-coupling-command-trace-')as d:
        work=Path(d)
        for name,value in [('process.tek',c['technology']),('input.asit',c['script']),('answers.txt',c['stdin']),('capture.gdb',commands)]:(work/name).write_text(value)
        run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=180)
        if run.returncode or not(work/'boundaries.json').exists():raise RuntimeError(run.stdout[-2000:]+run.stderr[-1500:])
        result=json.loads((work/'boundaries.json').read_text())
    assert result['input_bits']==p['input_bits'];assert result['output_bits']==p['value_bits'];assert result['control_before']==result['control_after']==0x37f
    out=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),gdb_commands=commands,math_instruction_points={hex(k):v for k,v in points.items()},reference='Same data-only entry/instruction and actual-return observers as mutual_command_traces_original, after counting actual cross-pair calls by original COUPLING return address 0x0804d113. Complete original creation and repeated/reversed COUPLING history is unchanged. The selected pair returns before the observer terminates the inferior; this is not native command termination.',cases=[dict(parent_case=92,parent_call=call,parent_pair=pair,label=c['label'],script=c['script'],stdin=c['stdin'],stdout=run.stdout,**result)])
    (ROOT/'tests/fixtures/coupling_command_traces_original.json').write_text(json.dumps(out,separators=(',',':'),allow_nan=False)+'\n');print('Original reversed COUPLING pair:',len(result['events']),'helper calls')


if __name__=='__main__':main()
