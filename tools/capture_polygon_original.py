"""Capture raw original polygon-spiral input/vertex stores at creator return."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from capture_original_symmetric import ORIGINAL_SHA256, LEGACY_SHA256

ROOT=Path(__file__).resolve().parents[1]
COMMANDS=r'''
set pagination off
set confirm off
set environment TERM dumb
set environment INPUTRC /dev/null
break *0x8057248
run -g -t process.tek -x input.asit < answers.txt
python
import gdb,struct,json
def memory(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def u32(a):return struct.unpack('<I',memory(a,4))[0]
def f64(a):return struct.unpack('<d',memory(a,8))[0]
control_before=int(gdb.parse_and_eval('$fctrl'))
esp=int(gdb.parse_and_eval('$esp'));ret=u32(esp);args=u32(esp+4)
config=[f64(args+0x80),u32(args+0x64),f64(args+0x88),f64(args+0x90),f64(args+0x98),f64(args+0xa0)]
gdb.Breakpoint('*'+hex(ret),temporary=True,internal=True)
gdb.execute('continue',to_string=True)
head=u32(0x80ce558);segment=u32(head+0xa8);rows=[]
while segment:
 assert len(rows)<20000
 rows.append(b''.join(memory(segment+offset,16)for offset in (0,24,0x44,0x5c,0x88,0xa0)).hex())
 segment=u32(segment+0xec)
result=dict(config=config,rows=rows,control_before=control_before,control_after=int(gdb.parse_and_eval('$fctrl')))
open('polygon.json','w').write(json.dumps(result))
end
kill
quit
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--library-path',required=True)
    args=parser.parse_args()
    original=args.reference/'run/asitic.linux.2.2';legacy=args.reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,sha in ((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise ValueError(f'Unexpected original checksum: {path}')
    technology=(args.reference/'run/tek/CMOS.tek').read_text();jobs=[]
    for sides in (3,4,5,6,8,12,16,32):
        for angle in (0,17,-35.5,179.9,360):
            jobs.append(dict(technology=technology,script=f'SPIRAL NAME=A:RAD=120:SIDES={sides}:W=3.25:S=2.125:N=2.375:METAL=M4:ORIENT={angle}:XORG=10:YORG=20\n',label=f'{sides} sides / {angle} degrees'))
    for name in ('network','gf180_network'):
        for index,c in enumerate(json.loads((ROOT/f'tests/fixtures/{name}.json').read_text())['cases']):
            if c['kind']=='polygon':jobs.append(dict(technology=c['technology'],script=c['script'],label=f'{name}/{index}'))
    records=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-polygon-') as directory:
        for index,c in enumerate(jobs):
            work=Path(directory)/str(index);work.mkdir()
            for name,text in (('process.tek',c['technology']),('input.asit',c['script']),('answers.txt','quit\n'),('capture.gdb',COMMANDS)):(work/name).write_text(text)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original.resolve())],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'polygon.json').exists():raise RuntimeError(f'Original polygon capture failed {c["label"]}: {run.stdout[-1500:]} {run.stderr[-1000:]}')
            item=json.loads((work/'polygon.json').read_text());item.update(c)
            if item['control_before']!=0x37f or item['control_after']!=0x37f:raise RuntimeError('Unexpected original control word')
            records.append(item);print(c['label'],len(item['rows']),'original segments',flush=True)
    result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,reference='Actual original CLI polygon creator 0x08057248 entry and actual return, with no function replacements. Config values are the actual parsed/quantized binary64 inputs. Every primary/outer/inner XY store is captured after original linked-order reversal and recentering; angles include parser conversion. Invalid/uninitialized mesh fields are excluded.',gdb_commands=COMMANDS,cases=records)
    (ROOT/'tests/fixtures/polygon_original.json').write_text(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
