"""Capture unchanged original square creators at their actual return stores."""
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
break *0x8056670
run -g -t process.tek -x input.asit < answers.txt
python
import gdb,struct,json
def memory(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def u32(a):return struct.unpack('<I',memory(a,4))[0]
def i32(a):return struct.unpack('<i',memory(a,4))[0]
def f64(a):return struct.unpack('<d',memory(a,8))[0]
control_before=int(gdb.parse_and_eval('$fctrl'))
esp=int(gdb.parse_and_eval('$esp'));ret=u32(esp);args=u32(esp+4)
config=dict(length=f64(args+0x70),height=f64(args+0x78),width=f64(args+0x88),spacing=f64(args+0x90),turns=f64(args+0x98),angle=f64(args+0xa0),metal=i32(args+0x68),exit_metal=i32(args+0x6c),phase=i32(args+0xac),x=f64(args+0x54),y=f64(args+0x5c))
mode=i32(esp+8);metal_count=i32(0x80d8904)
gdb.Breakpoint('*'+hex(ret),temporary=True,internal=True)
gdb.execute('continue',to_string=True)
head=u32(0x80ce558);segment=u32(head+0xa8);segments=[]
while segment:
 assert len(segments)<20000
 metal=i32(segment+0xdc)
 item=dict(coordinates_bits=b''.join(memory(segment+offset,24)for offset in(0,24,0x44,0x5c,0x88,0xa0)).hex(),width_bits=memory(segment+0xcc,8).hex(),metal=metal)
 if metal<metal_count:item['thickness_bits']=memory(segment+0xd4,8).hex()
 else:item['nx']=i32(segment+0xe0);item['ny']=i32(segment+0xe4)
 segments.append(item);segment=u32(segment+0xec)
result=dict(config=config,mode=mode,origin=[f64(head+0x54),f64(head+0x5c)],segments=segments,control_before=control_before,control_after=int(gdb.parse_and_eval('$fctrl')))
open('square.json','w').write(json.dumps(result))
end
kill
quit
'''


def jobs():
    for turns in(.25,.5,.75,1,1.25,1.5,1.75,2,2.75):
        for exit_metal in('-1','M3'):
            for angle in(0,17,-35.5):
                for phase in(1,-1):
                    script=f'SQUARE NAME=A:LEN=120.125:WID=100.375:W=3.25:S=2.125:N={turns}:METAL=M4:EXIT={exit_metal}:ORIENT={angle}:PHASE={phase}:XORG=12.345:YORG=23.456\n'
                    p=dict(name='A',length=120.125,height=100.375,width=3.25,spacing=2.125,turns=turns,metal='M4',exit_metal=exit_metal,angle=angle,phase=phase,x=12.345,y=23.456)
                    yield dict(label=f'keyword/{turns}/{exit_metal}/{angle}/{phase}',script=script,stdin='quit\n',parameters=p,native_keyword=True)
    for turns in(math.nextafter(1.75,0.),1.74999999,1.7499999,math.nextafter(1.75,math.inf),1.75000001,1.7500001):
        script=f'SQUARE NAME=A:LEN=120.125:WID=100.375:W=3.25:S=2.125:N={turns:.17g}:METAL=M4:EXIT=M3:ORIENT=0:PHASE=1:XORG=12.345:YORG=23.456\n'
        p=dict(name='A',length=120.125,height=100.375,width=3.25,spacing=2.125,turns=turns,metal='M4',exit_metal='M3',angle=0,phase=1,x=12.345,y=23.456)
        yield dict(label=f'keyword/turn-boundary/{turns:.17g}',script=script,stdin='quit\n',parameters=p,native_keyword=True)
    for turns in(1,1.25,1.5,1.75,2,2.75):
        for exit_metal in(False,True):
            answers=f'A\n120.123456789 100.987654321\n3.14159265358979\n2.71828182845905\n{turns}\nM4\n'+('y\nM3\n'if exit_metal else'n\n')+'12.3456789 23.456789\nquit\n'
            p=dict(name='A',length=120.123456789,height=100.987654321,width=3.14159265358979,spacing=2.71828182845905,turns=turns,metal='M4',exit_metal='M3'if exit_metal else'-1',angle=0,phase=1,x=12.3456789,y=23.456789)
            yield dict(label=f'interactive/{turns}/{exit_metal}',script='SQUARE\n',stdin=answers,parameters=p,native_keyword=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True)
    args=parser.parse_args();reference=args.reference.resolve()
    original=reference/'run/asitic.linux.2.2';legacy=reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,want in((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError(f'Unexpected oracle checksum: {path}')
    technology=(reference/'run/tek/CMOS.tek').read_text();records=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-square-')as directory:
        for i,c in enumerate(jobs()):
            work=Path(directory)/str(i);work.mkdir()
            for name,text in(('process.tek',technology),('input.asit',c['script']),('answers.txt',c['stdin']),('capture.gdb',COMMANDS)):(work/name).write_text(text)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'square.json').exists():raise RuntimeError(f'Original square capture failed {i}: {run.stdout[-1800:]} {run.stderr[-1000:]}')
            item=json.loads((work/'square.json').read_text())
            if item['control_before']!=0x37f or item['control_after']!=0x37f:raise RuntimeError('Unexpected original control word')
            item.update(c);records.append(item);print(f'Original square {i}: {len(item["segments"])} segments / {c["label"]}',flush=True)
    output=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,technology=technology,
                reference='Actual original square creator 0x08056670 entry and return, unchanged numerical instructions. Every XYZ store, scalar width, conductor thickness, metal and explicit via count captured after rotation and native linked/direction reversal; output origin and exact incoming parsed config retained. Native uninitialized conductor mesh counts and via thickness excluded.',gdb_commands=COMMANDS,cases=records)
    (ROOT/'tests/fixtures/square_original.json').write_text(json.dumps(output,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
