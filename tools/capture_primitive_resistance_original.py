"""Capture complete unchanged-original via resistance stores."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from capture_resistance_original import COMMANDS
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True)
    args=parser.parse_args();reference=args.reference.resolve();original=reference/'run/asitic.linux.2.2';legacy=reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,want in [(original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
    parent=ROOT/'tests/fixtures/primitive_original.json';f=json.loads(parent.read_text());records=[]
    jobs=[next(c for c in f['cases']if c['label']==f'interactive/via/{via}/7/5/{phase}')for via,phase in [('VIA1',1),('VIA2',-1),('VIA3',1),('VIA4',-1)]]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-via-resistance-')as directory:
        for i,c in enumerate(jobs):
            script=c['script']+'RESIS A\n'+''.join(f'RESISHF A {frequency}\n'for frequency in [.1,1,5,10,100,1000,1e6])
            work=Path(directory)/str(i);work.mkdir()
            for name,text in [('process.tek',f['technology']),('input.asit',script),('answers.txt',c['stdin']),('capture.gdb',COMMANDS)]:(work/name).write_text(text)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'resistance.json').exists():raise RuntimeError(run.stdout[-1600:]+run.stderr[-900:])
            raw=json.loads((work/'resistance.json').read_text());records.append(dict(parameters=c['parameters'],script=script,stdin=c['stdin'],**raw));print(f'Via resistance {i}',flush=True)
    out=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),technology=f['technology'],gdb_commands=COMMANDS,cases=records)
    (ROOT/'tests/fixtures/primitive_resistance_original.json').write_text(json.dumps(out,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
