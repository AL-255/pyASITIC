"""Capture complete original Pi2 sessions at fractional GHz parser boundaries."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import tempfile
from capture_pi_sessions import COMMANDS
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
from capture_transformer import TAP

ROOT=Path(__file__).resolve().parents[1]


def frequencies():
    values=[.1234567,.1,1/3,2.34567891,20.1234567]
    # Probe neighboring binary64 GHz inputs around binary32-Hz halfway
    # points. A binary64 multiplication followed by Math.fround can differ
    # from the original retained multiplication followed by FSTPS here.
    for hz in(1e6,123456700.,1.234e9,1.99e10):
        bits=struct.unpack('<I',struct.pack('<f',hz))[0]
        a,b=(struct.unpack('<f',struct.pack('<I',v))[0]for v in(bits,bits+1))
        center=((a+b)/2)/1e9
        values.extend((math.nextafter(center,0.),center,math.nextafter(center,math.inf)))
    return values


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--library-path',required=True)
    args=parser.parse_args();reference=args.reference.resolve()
    original=reference/'run/asitic.linux.2.2';legacy=reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,want in((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError(f'Unexpected oracle checksum: {path}')
    parent=ROOT/'tests/fixtures/pi_sessions_original.json';base=json.loads(parent.read_text())['cases'][0]
    request=dict(base['request']);request.pop('frequency_hz')
    coupled_parent=ROOT/'tests/fixtures/transformer_network.json'
    coupled_base=next(c for c in json.loads(coupled_parent.read_text())['cases']if c['first']['kind']=='transformer'and c['reference_mode']=='default'and c['first'].get('winding')==0)
    records=[];coupled_records=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-frequency-inputs-')as directory:
        for index,ghz in enumerate(frequencies()):
            work=Path(directory)/str(index);work.mkdir();text=format(ghz,'.17g')
            script=base['script'].replace('PI2 A 1\n',f'PI2 A {text}\n').replace('2PORT A 1 ',f'2PORT A {text} ')
            for name,value in(('process.tek',request['technology']),('input.asit',script),('answers.txt','quit\n'),('capture.gdb',COMMANDS)):
                (work/name).write_text(value)
            env=dict(os.environ,LD_LIBRARY_PATH=args.library_path)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=env,capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'raw.json').exists():raise RuntimeError(f'Original capture failed {index}: {run.stdout[-1000:]} {run.stderr[-1000:]}')
            raw=json.loads((work/'raw.json').read_text())
            if raw['control_before']!=0x37f or raw['control_after']!=0x37f:raise RuntimeError('Unexpected x87 control word')
            records.append(dict(command_ghz=text,request=dict(request,frequency_ghz=ghz),script=script,**raw))
            print(f'Captured original fractional-frequency session {index}: {text} GHz',flush=True)
        root=Path(directory);tap=root/'tap.cpp';tap.write_text(TAP)
        subprocess.run(['g++','-m32','-O2','-fPIC','-shared','-nostdlib','-fno-builtin',str(tap),'/lib/i386-linux-gnu/libc.so.6','-o',str(root/'tap.so')],check=True)
        for index in(0,3,9):
            c=records[index];work=root/f'coupled-{index}';work.mkdir();text=c['command_ghz']
            script=coupled_base['script'].replace('CALCTRANS A B 1\n',f'CALCTRANS A B {text}\n').replace('2PORTTRANS A B 1 1 1 ',f'2PORTTRANS A B {text} {text} 1 ')
            (work/'process.tek').write_text(coupled_base['technology']);(work/'input.asit').write_text(script)
            env=dict(os.environ,LD_PRELOAD=str(root/'tap.so'),LD_LIBRARY_PATH=args.library_path,TERM='dumb',INPUTRC='/dev/null')
            run=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],input=coupled_base['stdin'],capture_output=True,text=True,cwd=work,env=env,timeout=120,start_new_session=True)
            if run.returncode or not(work/'transformer-raw.out').exists():raise RuntimeError(f'Original coupled capture failed: {run.stdout[-1000:]} {run.stderr[-1000:]}')
            raw=(work/'transformer-raw.out').read_bytes()
            if len(raw)<23*8:raise RuntimeError('Missing original coupled raw stores')
            request={key:coupled_base[key]for key in('first','second','ground','technology','mesh','eddy','termination_ohm')}
            request.update(action='calctrans',frequency_ghz=c['request']['frequency_ghz'])
            coupled_records.append(dict(command_ghz=text,request=request,script=script,stdin=coupled_base['stdin'],frequency_bits=c['model']['M'][0],raw_output_bits=[raw[j:j+8].hex()for j in range(0,23*8,8)]))
            print(f'Captured original fractional coupled session: {text} GHz',flush=True)
    output=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),
                reference='Actual original CLI sessions; unchanged model/scattering/resonance entry and return observers. Fractional GHz text passes through the original type-5 parser. Midpoint neighbors exercise retained-scale to binary32 stores without a binary64 intermediate.',
                gdb_commands=COMMANDS,cases=records,coupled_parent_sha256=hashlib.sha256(coupled_parent.read_bytes()).hexdigest(),coupled_tap=TAP,coupled_cases=coupled_records)
    (ROOT/'tests/fixtures/frequency_inputs_original.json').write_text(json.dumps(output,separators=(',',':'))+'\n')


if __name__=='__main__':main()
