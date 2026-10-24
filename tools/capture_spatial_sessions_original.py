"""Complete unchanged original electrical sessions after spatial edit commands."""
import argparse,copy,gzip,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
from capture_pi_sessions import COMMANDS as PI_COMMANDS
from capture_paired_interactive_bounds_sessions import COMMANDS as COUPLED_COMMANDS
from capture_transformer import TAP
from capture_spatial_edits_original import command
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args();ref=a.reference.resolve();original=ref/'run/asitic.linux.2.2'
 for path,want in((original,ORIGINAL_SHA256),(ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
  if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
 wire=ROOT/'tests/fixtures/wire_sessions_original.json';paired=ROOT/'tests/fixtures/paired_interactive_bounds_sessions_original.json.gz'
 w=next(c for c in json.loads(wire.read_text())['cases']if c['request'].get('native_interactive')and c['request']['parameters']['width']>1 and not c['request']['eddy'])
 pcases=json.loads(gzip.decompress(paired.read_bytes()))['cases'];jobs=[('wire',w,[dict(command='MOVE',winding=0,x=1.23456789,y=2.34567891),dict(command='ROTATE',winding=0,angle=17.123456789),dict(command='FLIPV',winding=0)])]
 for c in(pcases[0],pcases[2]):jobs.append((c['request']['kind'],c,[dict(command='MOVE',winding=0,x=1.23456789,y=-2.34567891),dict(command='ROTATE',winding=0,angle=17.123456789),dict(command='FLIPV',winding=1),dict(command='FLIP',winding=1),dict(command='MOVETO',winding=1,x=50.123456789,y=60.987654321)]))
 records=[]
 with tempfile.TemporaryDirectory(prefix='pyasitic-original-spatial-models-')as directory:
  root=Path(directory);(root/'tap.cpp').write_text(TAP);subprocess.run(['g++','-m32','-O2','-fPIC','-shared','-nostdlib','-fno-builtin',str(root/'tap.cpp'),'/lib/i386-linux-gnu/libc.so.6','-o',str(root/'tap.so')],check=True)
  for label,c,edits in jobs:
   request=copy.deepcopy(c['request']);request.update(edits=edits,native_mesh=True);coupled=request['action']=='calctrans';names=['T-P','T-S']if label=='balun'else['A','B']if coupled else['A'];frequency=format(request['frequency_ghz'],'.17g')
   prefix=c['script'].split('CALCTRANS'if coupled else'PI2',1)[0];script=prefix+''.join(command(edit,names)for edit in edits)
   script+=(f'CALCTRANS {names[0]} {names[1]} {frequency}\n2PORTTRANS {names[0]} {names[1]} {frequency} {frequency} 1 S RECT s.out\n'if coupled else f'PI2 A {frequency}\n2PORT A {frequency} {frequency} 1 S RECT SLOW s.out\n')
   commands=COUPLED_COMMANDS.replace('TAP_PATH',str(root/'tap.so'))if coupled else PI_COMMANDS;work=root/label;work.mkdir()
   for name,value in(('process.tek',request['technology']),('input.asit',script),('answers.txt',c['stdin']),('capture.gdb',commands)):(work/name).write_text(value)
   run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),capture_output=True,text=True,start_new_session=True,timeout=180)
   if run.returncode or not(work/'raw.json').exists()or'Python Exception'in run.stderr:raise RuntimeError(label+run.stdout[-1500:]+run.stderr[-1500:])
   raw=json.loads((work/'raw.json').read_text())
   if coupled:
    data=(work/'transformer-raw.out').read_bytes();raw['raw_output_bits']=[data[i:i+8].hex()for i in range(0,len(data),8)]
   records.append(dict(label=label,request=request,script=script,stdin=c['stdin'],stdout=run.stdout,stderr=run.stderr,**raw));print(label,'captured',len(raw.get('raw_output_bits',[]))or len(raw['model']['M']),'model words',flush=True)
 result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in(wire,paired)},pi_gdb_commands=PI_COMMANDS,coupled_gdb_commands=COUPLED_COMMANDS,tap=TAP,reference='Unchanged original complete WIRE/BALUN/TRANS -> spatial edits -> Pi2/CALCTRANS/2PORT histories. Existing read-only model/scattering/resonance/node observers and nonnumerical sprintf observer. Every selected edited session retained without numerical replacements.',cases=records)
 with gzip.GzipFile(str(ROOT/'tests/fixtures/spatial_sessions_original.json.gz'),'wb',mtime=0)as out:out.write((json.dumps(result,separators=(',',':'),allow_nan=False)+'\n').encode())

if __name__=='__main__':main()
