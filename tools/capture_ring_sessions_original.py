"""Capture complete unchanged-original ring Pi2 electrical output stores."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from capture_pi_sessions import COMMANDS
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True)
    args=parser.parse_args();reference=args.reference.resolve()
    original=reference/'run/asitic.linux.2.2';legacy=reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,want in((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError(f'Unexpected oracle checksum: {path}')
    parent=ROOT/'tests/fixtures/ring_original.json';source=json.loads(parent.read_text());technology=source['technology']
    for key,value in(('chipx',128),('chipy',128),('fftx',64),('ffty',64)):
        technology=re.sub(rf'(?im)^(\s*{key}\s*=\s*)[\d.]+',rf'\g<1>{value}',technology)
    records=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-ring-sessions-')as directory:
        for i,(sides,gap,angle,frequency,eddy)in enumerate(((16,20,0,.1234567,False),(6,80,-35.5,2.34567891,False),(6,80,-35.5,1,True))):
            p=dict(name='A',metal='M4',radius=40,width=3,sides=sides,gap=gap,angle=angle,x=10,y=20)
            creation='RING NAME=A:METAL=M4:'+':'.join(f'{key}={p[name]:.17g}'for key,name in(('RAD','radius'),('W','width'),('SIDES','sides'),('GAP','gap'),('ORIENT','angle'),('XORG','x'),('YORG','y')))+'\n'
            text=format(frequency,'.17g');script='CELL 1000 1000 1000\nCCELL 1000 1000\n'+f'EDDY {"ON"if eddy else"OFF"}\n'+creation+f'PI2 A {text}\n2PORT A {text} {text} 1 S RECT SLOW s.out\n'
            work=Path(directory)/str(i);work.mkdir()
            for name,value in(('process.tek',technology),('input.asit',script),('answers.txt','quit\n'),('capture.gdb',COMMANDS)):(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'raw.json').exists():raise RuntimeError(f'Original ring session failed {i}: {run.stdout[-1600:]} {run.stderr[-1000:]}')
            raw=json.loads((work/'raw.json').read_text())
            if raw['control_before']!=0x37f or raw['control_after']!=0x37f:raise RuntimeError('Unexpected original control word')
            request=dict(action='pi2',kind='ring',native_keyword=True,parameters=p,technology=technology,frequency_ghz=frequency,eddy=eddy,mesh={key:1000 for key in('length_cell','width_cell','thickness_cell','capacitance_length_cell','capacitance_width_cell')})
            records.append(dict(request=request,script=script,**raw));print(f'Original ring electrical session {i}: eddy {eddy}',flush=True)
    output=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),gdb_commands=COMMANDS,
                reference='Unchanged original ring keyword creation followed by complete Pi2 and 2PORT sessions. Data-only model/S/resonance entry and return observers; every original Y/model/S store and retained resonance return preserved.',cases=records)
    (ROOT/'tests/fixtures/ring_sessions_original.json').write_text(json.dumps(output,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
