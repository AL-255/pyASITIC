"""Capture complete unchanged-original multi-metal Pi2 electrical stores."""
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
    parent=ROOT/'tests/fixtures/multimetal_original.json';technology=json.loads(parent.read_text())['technology']
    for key,value in(('chipx',256),('chipy',256),('fftx',128),('ffty',128)):
        technology=re.sub(rf'(?im)^(\s*{key}\s*=\s*)[\d.]+',rf'\g<1>{value}',technology)
    f=json.loads(parent.read_text());jobs=[f['cases'][i]for i in [0,81,124,173]]
    records=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-multimetal-sessions-')as directory:
        for i,c in enumerate(jobs):
            p=dict(c['parameters']);p.update(x=64,y=64);keyword=c['native_keyword']
            frequency=[.1234567,2.34567891,1.23456789,1.987654321][i];eddy=i in (1,3)
            creation=c['script'].replace(':XORG=12.345:YORG=23.456',':XORG=64:YORG=64')
            answers=c['stdin'].replace('12.3456789 23.456789','64 64')
            text=format(frequency,'.17g');script='CELL 1000 1000 1000\nCCELL 1000 1000\n'+f'EDDY {"ON"if eddy else"OFF"}\n'+creation+f'PI2 A {text}\n2PORT A {text} {text} 1 S RECT SLOW s.out\n'
            work=Path(directory)/str(i);work.mkdir()
            for name,value in(('process.tek',technology),('input.asit',script),('answers.txt',answers),('capture.gdb',COMMANDS)):(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'raw.json').exists():raise RuntimeError(f'Original multi-metal session failed {i}: {run.stdout[-1600:]} {run.stderr[-1000:]}')
            raw=json.loads((work/'raw.json').read_text())
            if raw['control_before']!=0x37f or raw['control_after']!=0x37f:raise RuntimeError('Unexpected original control word')
            request=dict(action='pi2',kind='multimetal',native_keyword=keyword,parameters=p,technology=technology,frequency_ghz=frequency,eddy=eddy,mesh={key:1000 for key in('length_cell','width_cell','thickness_cell','capacitance_length_cell','capacitance_width_cell')})
            records.append(dict(request=request,script=script,stdin=answers,**raw));print(f'Original multi-metal electrical session {i}: keyword {keyword}, eddy {eddy}',flush=True)
        invalid=[]
        for bottom in ['M5','M1','M4']:
            bad=records[0];script=bad['script'].replace(':EXIT=M3',':EXIT='+bottom)
            if bottom!='M5':script=script.replace(':METAL=M5',':METAL=M1')
            work=Path(directory)/('invalid-'+bottom);work.mkdir();(work/'process.tek').write_text(technology);(work/'input.asit').write_text(script)
            run=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path,TERM='dumb',INPUTRC='/dev/null'),input='quit\n',capture_output=True,text=True,start_new_session=True,timeout=120)
            if 'Must specify more than one metal layer'not in run.stdout:raise RuntimeError('Missing native invalid multi-metal stack diagnostic: '+run.stdout[-1000:])
            request=dict(bad['request'],parameters=dict(bad['request']['parameters'],metal='M5'if bottom=='M5'else'M1',bottom_metal=bottom))
            invalid.append(dict(request=request,script=script,stdin='quit\n',returncode=run.returncode,stdout=run.stdout,stderr=run.stderr))
    output=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),gdb_commands=COMMANDS,
                reference='Unchanged original multi-metal keyword/interactive creation followed by complete Pi2 and 2PORT sessions. Data-only model/S/resonance entry and return observers preserve every original Y/model/S store and retained resonance return. Three invalid same/reversed-metal stacks retain the original failure transcripts.',cases=records,invalid_cases=invalid)
    (ROOT/'tests/fixtures/multimetal_sessions_original.json').write_text(json.dumps(output,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
