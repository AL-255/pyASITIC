"""Capture complete unchanged-original symmetric-coil Pi2 electrical stores."""
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
    parent=ROOT/'tests/fixtures/symmetric_geometry_original.json';technology=json.loads(parent.read_text())['technology']
    original_technology=technology
    for key,value in(('chipx',256),('chipy',256),('fftx',128),('ffty',128)):
        technology=re.sub(rf'(?im)^(\s*{key}\s*=\s*)[\d.]+',rf'\g<1>{value}',technology)
    parent_data=json.loads(parent.read_text())
    # Cross both algorithms, crossover histories, native rotations, phase and
    # full binary64 interactive construction with complete electrical solves.
    indices=[0,10,21,24,53,77,100,101]
    jobs=[parent_data['cases'][i]for i in indices]
    records=[];invalid=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-symmetric-sessions-')as directory:
        for i,c in enumerate(jobs):
            p=dict(c['parameters']);kind=c['kind'];keyword=c['native_keyword']
            frequency=[.1234567,2.34567891,1.23456789,1,3.45678912,1.987654321,2.12345678,1][i]
            eddy=i in (1,3,7)
            # A centered layout keeps rotated square and polygon contacts in chip.
            if keyword:
                creation=c['script'].replace(':XORG=12.345:YORG=23.456',':XORG=100:YORG=80')
                p.update(x=100,y=80);answers=c['stdin']
            else:
                creation=c['script'];answers=c['stdin'].replace('12.3456789 23.456789','100 80');p.update(x=100,y=80)
            text=format(frequency,'.17g');script='CELL 1000 1000 1000\nCCELL 1000 1000\n'+f'EDDY {"ON"if eddy else"OFF"}\n'+creation+f'PI2 A {text}\n2PORT A {text} {text} 1 S RECT SLOW s.out\n'
            work=Path(directory)/str(i);work.mkdir()
            for name,value in(('process.tek',technology),('input.asit',script),('answers.txt',answers),('capture.gdb',COMMANDS)):(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'raw.json').exists():raise RuntimeError(f'Original symmetric session failed {i}: {run.stdout[-1600:]} {run.stderr[-1000:]}')
            raw=json.loads((work/'raw.json').read_text())
            if raw['control_before']!=0x37f or raw['control_after']!=0x37f:raise RuntimeError('Unexpected original control word')
            request=dict(action='pi2',kind=kind,native_keyword=keyword,parameters=p,technology=technology,frequency_ghz=frequency,eddy=eddy,mesh={key:1000 for key in('length_cell','width_cell','thickness_cell','capacitance_length_cell','capacitance_width_cell')})
            records.append(dict(request=request,script=script,stdin=answers,**raw));print(f'Original symmetric electrical session {i}: keyword {keyword}, eddy {eddy}',flush=True)
        bad=records[0];bad_technology=original_technology
        for key,value in(('chipx',128),('chipy',128),('fftx',64),('ffty',64)):
            bad_technology=re.sub(rf'(?im)^(\s*{key}\s*=\s*)[\d.]+',rf'\g<1>{value}',bad_technology)
        script=bad['script'].replace(':XORG=100:YORG=80',':XORG=64:YORG=40')
        work=Path(directory)/'invalid';work.mkdir();(work/'process.tek').write_text(bad_technology);(work/'input.asit').write_text(script)
        run=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path,TERM='dumb',INPUTRC='/dev/null'),input='quit\n',capture_output=True,text=True,start_new_session=True,timeout=120)
        if 'Error:  Coordinate out of range.'not in run.stdout:raise RuntimeError('Expected original symmetric coordinate diagnostic')
        request=dict(bad['request'],technology=bad_technology,parameters=dict(bad['request']['parameters'],x=64,y=40))
        invalid.append(dict(request=request,script=script,stdin='quit\n',returncode=run.returncode,stdout=run.stdout,stderr=run.stderr))
    output=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),gdb_commands=COMMANDS,
                reference='Unchanged original symmetric square/polygon keyword/interactive creation followed by complete Pi2 and 2PORT sessions. Data-only model/S/resonance entry and return observers preserve every original Y/model/S store and retained resonance return.',cases=records,invalid_cases=invalid)
    (ROOT/'tests/fixtures/symmetric_sessions_original.json').write_text(json.dumps(output,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
