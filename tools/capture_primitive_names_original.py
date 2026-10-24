"""Read original interactive WIRE/CAPACITOR/VIA names and constructor stores."""
import argparse,gzip,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
from capture_wire_original import COMMANDS as WIRE
from capture_primitive_original import COMMANDS as PRIMITIVE,JOIN
ROOT=Path(__file__).resolve().parents[1]


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args();ref=a.reference.resolve();original=ref/'run/asitic.linux.2.2'
 for path,want in((original,ORIGINAL_SHA256),(ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
  if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
 technology=(ROOT/'src/reasitic/CMOS.tek').read_text();cases=[]
 with tempfile.TemporaryDirectory(prefix='pyasitic-original-primitive-names-')as d:
  for kind in('wire','capacitor','via'):
   for name in('  miXed   Coil  ','coil\t alpha','a-b_7'):
    parameters=dict(name=name,x=12.3456789,y=23.456789)
    if kind=='wire':
     parameters.update(length=80.123456789,width=3.14159265358979,metal='M4',phase=-1,angle=37.)
     answers=[name,'80.123456789','3.14159265358979','M4','-1','12.3456789 23.456789','37'];commands=WIRE.replace('wire.json','primitive.json')
    elif kind=='capacitor':
     parameters.update(length=80.123456789,width=3.14159265358979,metal='M5',bottom_metal='M3',angle=-35.5)
     answers=[name,'80.123456789','3.14159265358979','M5','M3','12.3456789 23.456789','-35.5'];commands=PRIMITIVE.replace('ENTRY','0x8057998').replace("gdb.Breakpoint('*'+hex(ret),temporary=True,internal=True)",JOIN+"gdb.Breakpoint('*'+hex(ret),temporary=True,internal=True)")
    else:
     parameters.update(via='VIA4',nx=2,ny=3,phase=-1)
     answers=[name,'VIA4','2','3','-1','12.3456789 23.456789'];commands=PRIMITIVE.replace('ENTRY','0x8057b78')
    commands=commands.replace('result=dict(',"result=dict(name=memory(head,80).split(b'\\0',1)[0].decode('latin1'),")
    work=Path(d)/str(len(cases));work.mkdir();script=kind.upper()+'\n';stdin='\n'.join(answers+['quit'])+'\n'
    for key,value in(('process.tek',technology),('input.asit',script),('answers.txt',stdin),('capture.gdb',commands)):(work/key).write_text(value)
    run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
    if run.returncode or not(work/'primitive.json').exists()or'Python Exception'in run.stderr:raise RuntimeError(kind+repr(name)+run.stdout[-1200:]+run.stderr[-1000:])
    item=json.loads((work/'primitive.json').read_text());cases.append(dict(kind=kind,parameters=parameters,native_interactive=True,script=script,stdin=stdin,stdout=run.stdout,stderr=run.stderr,**item));print(kind,repr(name),'->',repr(item['name']),flush=True)
 result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,technology=technology,reference='Unchanged original interactive primitive prompts and constructors; actual constructor return name, origin and all segment stores. Read-only GDB observers reused from wire/primitive captures; no numerical substitutions.',wire_commands=WIRE,primitive_commands=PRIMITIVE,capacitor_join_commands=JOIN,cases=cases)
 with gzip.GzipFile(str(ROOT/'tests/fixtures/primitive_names_original.json.gz'),'wb',mtime=0)as out:out.write((json.dumps(result,separators=(',',':'),allow_nan=False)+'\n').encode())

if __name__=='__main__':main()
