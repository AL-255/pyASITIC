"""Capture unchanged original ring creator inputs and every raw XY store."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256

ROOT=Path(__file__).resolve().parents[1]
COMMANDS=r'''
set pagination off
set confirm off
set environment TERM dumb
set environment INPUTRC /dev/null
break *0x805b450
run -g -t process.tek -x input.asit < answers.txt
python
import gdb,struct,json
def memory(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def u32(a):return struct.unpack('<I',memory(a,4))[0]
def f64(a):return struct.unpack('<d',memory(a,8))[0]
control_before=int(gdb.parse_and_eval('$fctrl'))
esp=int(gdb.parse_and_eval('$esp'));ret=u32(esp);args=u32(esp+4)
config=[f64(args+0x80),u32(args+0x64),f64(args+0x88),f64(args+0x90),f64(args+0xa0)]
origin=[f64(args+0x54),f64(args+0x5c)]
gdb.Breakpoint('*'+hex(ret),temporary=True,internal=True)
gdb.execute('continue',to_string=True)
head=u32(0x80ce558);segment=u32(head+0xa8);rows=[]
while segment:
 assert len(rows)<20000
 rows.append(b''.join(memory(segment+offset,16)for offset in (0,24,0x44,0x5c,0x88,0xa0)).hex())
 segment=u32(segment+0xec)
result=dict(config=config,origin=origin,rows=rows,control_before=control_before,control_after=int(gdb.parse_and_eval('$fctrl')))
open('ring.json','w').write(json.dumps(result))
end
kill
quit
'''


def jobs():
    for sides in(3,4,5,6,8,16,32,128):
        for gap,angle in((0,0),(20,17),(41.375,-35.5),(179.9,179.9),(360,360)):
            yield dict(radius=120,width=3.25,sides=sides,gap=gap,angle=angle,x=10,y=20)
    for radius in(40.1234567,math.nextafter(120.00000381469727,0.),120.00000381469727,math.nextafter(120.00000381469727,math.inf)):
        yield dict(radius=radius,width=3.14159265,sides=17,gap=.1234567,angle=-.1234567,x=12.3456789,y=23.456789)
    yield dict(radius=40,width=3,sides=16,gap=20,angle=0,x=0,y=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True)
    args=parser.parse_args();reference=args.reference.resolve()
    original=reference/'run/asitic.linux.2.2';legacy=reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,want in((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError(f'Unexpected oracle checksum: {path}')
    technology=(reference/'run/tek/CMOS.tek').read_text();records=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-ring-')as directory:
        for i,p in enumerate(jobs()):
            work=Path(directory)/str(i);work.mkdir();p=dict(name='A',metal='M4',**p)
            script='RING NAME=A:METAL=M4:'+':'.join(f'{key}={p[name]:.17g}'for key,name in(('RAD','radius'),('W','width'),('SIDES','sides'),('GAP','gap'),('ORIENT','angle'),('XORG','x'),('YORG','y')))+'\n'
            for name,text in(('process.tek',technology),('input.asit',script),('answers.txt','quit\n'),('capture.gdb',COMMANDS)):(work/name).write_text(text)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'ring.json').exists():raise RuntimeError(f'Original ring capture failed {i}: {run.stdout[-1500:]} {run.stderr[-1000:]}')
            item=json.loads((work/'ring.json').read_text())
            if item['control_before']!=0x37f or item['control_after']!=0x37f:raise RuntimeError('Unexpected original control word')
            item.update(parameters=p,script=script);records.append(item);print(f'Original ring {i}: {len(item["rows"])} segments',flush=True)
    output=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,technology=technology,
                reference='Actual original ring creator 0x0805b450 entry and return; data-only gdb observers leave every numerical instruction unchanged. Parsed config and origin plus every center/outer/inner XY store after linked-order reversal and recentering. Uninitialized segment mesh counts excluded.',gdb_commands=COMMANDS,cases=records)
    (ROOT/'tests/fixtures/ring_original.json').write_text(json.dumps(output,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
