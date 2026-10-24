"""Capture complete unchanged-original capacitor Pi2 electrical stores."""
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
    parent=ROOT/'tests/fixtures/primitive_original.json';technology=json.loads(parent.read_text())['technology']
    for key,value in(('chipx',256),('chipy',256),('fftx',128),('ffty',128)):
        technology=re.sub(rf'(?im)^(\s*{key}\s*=\s*)[\d.]+',rf'\g<1>{value}',technology)
    f=json.loads(parent.read_text());jobs=[f['cases'][i]for i in [0,5,53,12]]
    records=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-primitive-sessions-')as directory:
        for i,c in enumerate(jobs):
            p=dict(c['parameters']);p.update(x=64,y=64);keyword=c.get('native_keyword',False);interactive=c.get('native_interactive',False)
            frequency=[.1234567,2.34567891,1.23456789,1][i];eddy=i in (1,2)
            creation=c['script'].replace(':XORG=12.345:YORG=23.456',':XORG=64:YORG=64')
            answers=c['stdin'].replace('12.3456789 23.456789','64 64')
            text=format(frequency,'.17g');script='CELL 1000 1000 1000\nCCELL 1000 1000\n'+f'EDDY {"ON"if eddy else"OFF"}\n'+creation+f'PI2 A {text}\n2PORT A {text} {text} 1 S RECT SLOW s.out\n'
            work=Path(directory)/str(i);work.mkdir()
            for name,value in(('process.tek',technology),('input.asit',script),('answers.txt',answers),('capture.gdb',COMMANDS)):(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'raw.json').exists():raise RuntimeError(f'Original capacitor session failed {i}: {run.stdout[-1600:]} {run.stderr[-1000:]}')
            raw=json.loads((work/'raw.json').read_text())
            if raw['control_before']!=0x37f or raw['control_after']!=0x37f:raise RuntimeError('Unexpected original control word')
            request=dict(action='pi2',kind='capacitor',native_keyword=keyword,native_interactive=interactive,parameters=p,technology=technology,frequency_ghz=frequency,eddy=eddy,mesh={key:1000 for key in('length_cell','width_cell','thickness_cell','capacitance_length_cell','capacitance_width_cell')})
            records.append(dict(request=request,script=script,stdin=answers,**raw));print(f'Original capacitor electrical session {i}: keyword {keyword}, eddy {eddy}',flush=True)
        faults=[]
        c=next(c for c in f['cases']if c['label']=='interactive/via/VIA1/2.9/3.9/-1')
        script='CELL 1000 1000 1000\nCCELL 1000 1000\n'+c['script']+'RESIS A\nRESISHF A 1\nPI2 A 1\n'
        work=Path(directory)/'via-fault';work.mkdir();(work/'process.tek').write_text(technology);(work/'input.asit').write_text(script)
        run=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path,TERM='dumb',INPUTRC='/dev/null'),input=c['stdin'],capture_output=True,text=True,start_new_session=True,timeout=120)
        if run.returncode!=-11 or 'Performing Analysis'not in run.stdout:raise RuntimeError('Original standalone via Pi2 fault changed: '+run.stdout[-900:])
        request=dict(action='pi2',kind='via',native_interactive=True,parameters=c['parameters'],technology=technology,frequency_ghz=1)
        faults.append(dict(request=request,script=script,stdin=c['stdin'],returncode=run.returncode,stdout=run.stdout,stderr=run.stderr))
    output=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),gdb_commands=COMMANDS,
                reference='Unchanged original capacitor keyword/interactive creation followed by complete Pi2 and 2PORT sessions. Data-only model/S/resonance entry and return observers preserve every original Y/model/S store and retained resonance return. One standalone VIA Pi2 session retains the original signal-11 fault transcript.',cases=records,via_faults=faults)
    (ROOT/'tests/fixtures/primitive_sessions_original.json').write_text(json.dumps(output,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
