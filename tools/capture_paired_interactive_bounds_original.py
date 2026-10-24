"""Unchanged original interactive paired floor/capacity and chip-boundary stores."""
import argparse,gzip,hashlib,json,math,os,re,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
from capture_paired_original import COMMANDS
ROOT=Path(__file__).resolve().parents[1]


def jobs():
 base=dict(name='T',primary_name='A',secondary_name='B',width=5.,secondary_width=4.375,spacing=3.,metal='M4',secondary_metal='M3',exit_metal='M3',x=12.3456789,y=23.456789)
 for length,turns in[(60.,3.25),(60.,3.75),(60.,3.99),(60.,math.nextafter(4.,0.)),(80.,5.0000001),(80.,5.25),(80.,5.99),(80.,math.nextafter(6.,0.))]:
  yield 'balun',f'floor/{length}/{turns:.17g}',dict(base,length=length,turns=turns),False
 for length in(160.,200.):
  yield 'balun',f'non-square/{length}',dict(base,length=length,turns=5.99),True
 for turns in(1.,1.25,2.5,math.nextafter(2.75,0.),2.75):
  for exit in('M3','-1'):
   yield 'transformer',f'shared-turns/{turns:.17g}/{exit}',dict(base,length=80.123456789,height=80.987654321,turns=turns,secondary_turns=999,exit_metal=exit),False


def answers(kind,p):
 n=lambda k:format(p[k],'.17g')
 if kind=='balun':lines=[p['name'],n('length'),n('width'),n('spacing'),n('secondary_width'),n('turns'),p['metal'],p['secondary_metal']]
 else:lines=[p['primary_name'],p['secondary_name'],n('length')+' '+n('height'),n('width'),n('spacing'),n('turns'),p['metal'],*(['n']if p['exit_metal']=='-1'else['y',p['exit_metal']])]
 return '\n'.join(lines+[n('x')+' '+n('y'),'quit'])+'\n'


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args();ref=a.reference.resolve();original=ref/'run/asitic.linux.2.2'
 for path,expected in((original,ORIGINAL_SHA256),(ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
  if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Unexpected original checksum')
 records=[];base=(ROOT/'src/reasitic/CMOS.tek').read_text()
 with tempfile.TemporaryDirectory(prefix='pyasitic-original-paired-bounds-')as d:
  for index,(kind,label,parameters,nonsquare)in enumerate(jobs()):
   technology=base
   if nonsquare:
    for key,value in(('chipx',256),('chipy',128),('fftx',64),('ffty',64)):technology=re.sub(rf'(?im)^(\s*{key}\s*=\s*)[\d.]+',rf'\g<1>{value}',technology)
   work=Path(d)/str(index);work.mkdir();script='BALUN\n'if kind=='balun'else'TRANS\n';stdin=answers(kind,parameters);commands=COMMANDS.replace('ENTRY',hex(0x80576d4 if kind=='transformer'else 0x8059854)).replace('KIND',repr(kind))
   for name,value in(('process.tek',technology),('input.asit',script),('answers.txt',stdin),('capture.gdb',commands)):(work/name).write_text(value)
   run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
   if run.returncode or not(work/'paired.json').exists()or'Python Exception'in run.stderr or'Traceback'in run.stderr:raise RuntimeError(label+': '+run.stdout[-2000:]+run.stderr[-1500:])
   records.append(dict(kind=kind,label=label,parameters=parameters,technology=technology,native_interactive=True,script=script,stdin=stdin,stdout=run.stdout,stderr=run.stderr,**json.loads((work/'paired.json').read_text())));print(index,label,[c['turns']for c in records[-1]['configs']],flush=True)
 result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,gdb_commands=COMMANDS,reference='Unchanged complete original TRANS/BALUN interactive creators. Read-only constructor/actual-return data observations. Balun floors total turns before capacity comparison; non-square chip dimensions use the original prompt bounds. Both original descriptors, winding XYZ/origin/width/thickness/metal/via stores, linkage and control words retained. No numerical or runtime replacement.',cases=records)
 with gzip.GzipFile(str(ROOT/'tests/fixtures/paired_interactive_bounds_original.json.gz'),'wb',mtime=0)as f:f.write((json.dumps(result,separators=(',',':'),allow_nan=False)+'\n').encode())

if __name__=='__main__':main()
