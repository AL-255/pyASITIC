"""Read-only original CELL/CCELL globals, counts, LMAT and complete Pi2 outputs."""
import argparse,hashlib,json,os,struct,subprocess,sys,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
from capture_mesh_sessions_original import COMMANDS as LMAT_COMMANDS
from capture_pi_sessions import COMMANDS as PI_COMMANDS
from capture_impedance_original import COMMANDS as ASSEMBLY_COMMANDS
ROOT=Path(__file__).resolve().parents[1]
KEYS=('length_cell','width_cell','thickness_cell','capacitance_length_cell','capacitance_width_cell')
# Positive decimal inputs on opposite sides of retained counting / cloning boundaries.
CELLS=[(1000,1.90476189,1000,1000,1000),
       (20.0000001,3.3333333,.33333333,20.0000001,3.3333333),
       (33.3333333,1.90476189,.49999999,26.6666667,1.42857145),
       (39.9999999,2.00000001,1.00000001,39.9999999,20.0000001),
       (40.0000001,1.90476191,1.00000001,40.0000001,19.9999999),
       (1000,.100000001,1000,1000,1000)]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args()
 original=a.reference.resolve()/'run/asitic.linux.2.2';legacy=a.reference.resolve()/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
 for path,expected in((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
  if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Unexpected original checksum')
 tech=(ROOT/'src/reasitic/CMOS.tek').read_text();cases=[]
 # Record every selected cell global at the original model boundary, plus the
 # existing unmodified model / scattering / resonance observations.
 pi_commands=PI_COMMANDS.replace("if kind=='model':item.update(Y=ports()", "if kind=='model':item.update(mesh_bits=memory(0x80ce580,40).hex(),chip_bits=memory(0x80ce980,24).hex(),Y=ports()")
 with tempfile.TemporaryDirectory(prefix='pyasitic-original-mesh-inputs-')as d:
  for index,cells in enumerate(CELLS):
   mesh=dict(zip(KEYS,cells));request=dict(kind='wire',native_keyword=True,parameters=dict(name='A',length=40,width=20,metal='M5',x=40,y=40),technology=tech,frequency_ghz=1.,mesh=mesh,native_mesh=True)
   script='CELL '+' '.join(format(v,'.17g')for v in cells[:3])+'\nCCELL '+' '.join(format(v,'.17g')for v in cells[3:])+'\nWIRE NAME=A:LEN=40:WID=20:METAL=M5:XORG=40:YORG=40\n'
   item=dict(request=request,script=script)
   for mode,commands,suffix in(('lmat',LMAT_COMMANDS,'LMAT A 1\n'),('pi2',pi_commands,'PI2 A 1\n2PORT A 1 1 1 Y RECT SLOW y.out\n2PORT A 1 1 1 S RECT SLOW s.out\n'),('assembly',ASSEMBLY_COMMANDS,'LMAT A 1\n')):
    work=Path(d)/f'{index}-{mode}';work.mkdir()
    for name,value in(('process.tek',tech),('input.asit',script+suffix),('answers.txt','quit\n'),('capture.gdb',commands)):(work/name).write_text(value)
    run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),capture_output=True,text=True,start_new_session=True,timeout=180)
    output=work/('assembly.json'if mode=='assembly'else'raw.json')
    if run.returncode or not output.exists()or'Python Exception'in run.stderr or'Traceback'in run.stderr:raise RuntimeError(f'{index}/{mode}: '+run.stdout[-2400:]+run.stderr[-1800:])
    item[mode]=dict(json.loads(output.read_text()),stdout=run.stdout,stderr=run.stderr,script=script+suffix)
   cases.append(item);print(index,'original filaments',item['lmat']['counts'][0]['total'],'Pi model stores',len(item['pi2']['model']['M']),flush=True)
 out=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,reference='Unchanged original CELL/CCELL CLI input histories; read-only globals/entry/return observations, all count and constructed-filament stores, actual LMAT report arguments, complete Pi2 Y/model/S/resonance stores. No numerical, allocator or runtime replacement. Default type-7 retained micrometre scaling, 0.1-micrometre snap and CCELL pitch clamps are observed, alongside complete assembly/factor/inverse/reduction stores. Typed binary64 mesh requests are a separate API boundary.',lmat_commands=LMAT_COMMANDS,pi_commands=pi_commands,assembly_commands=ASSEMBLY_COMMANDS,cases=cases)
 import gzip
 with gzip.GzipFile(str(ROOT/'tests/fixtures/mesh_inputs_original.json.gz'),'wb',mtime=0)as f:f.write((json.dumps(out,separators=(',',':'),allow_nan=False)+'\n').encode())
 subprocess.run([sys.executable,str(ROOT/'tools/capture_mesh_input_inverses_original.py'),'--reference',str(a.reference),'--library-path',a.library_path],check=True,start_new_session=True)

if __name__=='__main__':main()
