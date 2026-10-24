"""Full original models selecting copied, renamed and relinked scene windings."""
import argparse,copy,gzip,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
from capture_pi_sessions import COMMANDS as PI_COMMANDS
from capture_paired_interactive_bounds_sessions import COMMANDS as COUPLED_COMMANDS
from capture_spatial_edits_original import COMMANDS as GEOMETRY_COMMANDS
from capture_copy_links_original import command
from capture_transformer import TAP
ROOT=Path(__file__).resolve().parents[1]
SNAPSHOT=GEOMETRY_COMMANDS.split('python\n',1)[1].split('\nend\nrun',1)[0].replace('class Observe','class Snapshot').replace("Observe('*", "Snapshot('*")


def jobs():
 wire=ROOT/'tests/fixtures/wire_sessions_original.json';paired=ROOT/'tests/fixtures/paired_interactive_bounds_sessions_original.json.gz'
 w=next(c for c in json.loads(wire.read_text())['cases']if c['request'].get('native_interactive')and c['request']['parameters']['width']>1 and not c['request']['eddy'])
 edits=[dict(command='COPY',winding=0,name='b',metal='M3',x=35.123456789,y=34.987654321),dict(command='COPY',winding=0,name='c'),dict(command='MOVETO',winding=2,x=50.123456789,y=60.987654321),dict(command='BEFRIEND',winding=1,other=2),dict(command='MOVE',winding=1,x=3.25,y=-2.75),dict(command='RENAME',winding=2,name='c_final')]
 for variant in('pi2','calctrans','pi2-reference'):
  action='pi2'if variant=='pi2-reference'else variant
  r=copy.deepcopy(w['request']);r.update(action=action,edits=edits,native_mesh=True,winding=2)
  if action=='calctrans':r.update(first_winding=2,second_winding=0,termination_ohm=0)
  if variant=='pi2-reference':r['ground']={**{k:r[k]for k in('kind','parameters','edits','native_interactive')},'winding':0}
  yield 'wire/'+variant,wire,r,w['script'].split('PI2',1)[0],w['stdin'],['A']
 c=json.loads(gzip.decompress(paired.read_bytes()))['cases'][0];r=copy.deepcopy(c['request']);r.update(winding=2,first_winding=2,second_winding=1,edits=[dict(command='COPY',winding=0,name='c',metal='M2'),dict(command='MOVETO',winding=2,x=80.123456789,y=50.987654321),dict(command='BEFRIEND',winding=0,other=2),dict(command='MOVE',winding=1,x=.125,y=-.25),dict(command='RENAME',winding=2,name='copied')])
 yield 'balun/calctrans',paired,r,c['script'].split('CALCTRANS',1)[0],c['stdin'],['T-P','T-S']
 primitive=ROOT/'tests/fixtures/primitive_original.json';p=json.loads(primitive.read_text());c=next(c for c in p['cases']if c['kind']=='via')
 r=dict(action='pi2',kind='via',parameters=copy.deepcopy(c['parameters']),native_interactive=True,native_mesh=True,technology=p['technology'],frequency_ghz=1.23456789,eddy=False,winding=1,
        mesh=dict(length_cell=1000,width_cell=1000,thickness_cell=1000,capacitance_length_cell=1000,capacitance_width_cell=1000),edits=[dict(command='COPY',winding=0,name='c',metal='M2',x=40,y=40)])
 yield 'via/copied-metal-pi2',primitive,r,'CELL 1000 1000 1000\nCCELL 1000 1000\nEDDY OFF\n'+c['script'],c['stdin'],['A']

def main(*,output_name='copy_sessions_original',job_source=jobs,command_source=command,description=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args();ref=a.reference.resolve();original=ref/'run/asitic.linux.2.2'
 for path,want in((original,ORIGINAL_SHA256),(ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
  if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
 records=[];parents={};cap_reference_failures=[]
 with tempfile.TemporaryDirectory(prefix='pyasitic-original-copy-models-')as directory:
  root=Path(directory);(root/'tap.cpp').write_text(TAP);subprocess.run(['g++','-m32','-O2','-fPIC','-shared','-nostdlib','-fno-builtin',str(root/'tap.cpp'),'/lib/i386-linux-gnu/libc.so.6','-o',str(root/'tap.so')],check=True)
  for label,parent,r,prefix,stdin,names in job_source():
   parents[parent.name]=hashlib.sha256(parent.read_bytes()).hexdigest();script=prefix
   for op in r['edits']:
    script+=command_source(op,names)
    if op['command']=='COPY':names.append(op['name'].upper())
    elif op['command']=='RENAME':names[op['winding']]=op['name'].upper()
   first=names[r['winding']];frequency=format(r['frequency_ghz'],'.17g');snapshot=names[0]if r['kind']=='via'else first;script+=f'GEOM {snapshot}\n';coupled=r['action']=='calctrans'
   if coupled:
    second=names[r['second_winding']];script+=f'CALCTRANS {first} {second} {frequency}\n2PORTTRANS {first} {second} {frequency} {frequency} 1 S RECT s.out\n'
    commands=COUPLED_COMMANDS.replace('TAP_PATH',str(root/'tap.so')).replace('dict(records=records,nodes=nodes,signal=signal,pending=', 'dict(geometry_states=states,records=records,nodes=nodes,signal=signal,pending=')
   else:
    suffix=' '+names[r['ground']['winding']]if r.get('ground')else''
    script+=f'PI2 {first} {frequency}{suffix}\n2PORT {first} {frequency} {frequency} 1 S RECT SLOW s.out{suffix}\n';commands=PI_COMMANDS.replace("open('raw.json'", "result.update(geometry_states=states)\nopen('raw.json'")
   commands=commands.replace('end\nrun -g',SNAPSHOT+'\nend\nrun -g');work=root/str(len(records));work.mkdir()
   for name,value in(('process.tek',r['technology']),('input.asit',script),('answers.txt',stdin),('capture.gdb',commands)):(work/name).write_text(value)
   run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),capture_output=True,text=True,start_new_session=True,timeout=180)
   if run.returncode or not(work/'raw.json').exists()or'Python Exception'in run.stderr:raise RuntimeError(label+run.stdout[-1800:]+run.stderr[-1800:])
   raw=json.loads((work/'raw.json').read_text());assert len(raw['geometry_states'])==1
   if coupled:
    data=(work/'transformer-raw.out').read_bytes();raw['raw_output_bits']=[data[i:i+8].hex()for i in range(0,len(data),8)]
   records.append(dict(label=label,request=r,script=script,stdin=stdin,stdout=run.stdout,stderr=run.stderr,**raw));print(label,'captured',flush=True)
  via=next(c for c in records if c['label']=='via/copied-metal-pi2');r=copy.deepcopy(via['request']);r.update(action='capacitance',mesh=dict(length_cell=1000,width_cell=1000),ground={k:copy.deepcopy(r[k])for k in('kind','parameters','edits','native_interactive')});r['ground']['winding']=0
  script=via['script'].split('GEOM',1)[0]+'CAP C 1.23456789 A\n';work=root/'cap-reference';work.mkdir()
  for name,value in(('process.tek',r['technology']),('input.asit',script)):(work/name).write_text(value)
  run=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),input=via['stdin'],capture_output=True,text=True,start_new_session=True,timeout=120)
  if run.returncode or'Total Capacitance =  -nan'not in run.stdout or'Total Resistance =  -nan'not in run.stdout:raise RuntimeError('Unexpected converted-VIA CAP reference outcome: '+run.stdout[-1500:]+run.stderr[-1000:])
  cap_reference_failures.append(dict(label=via['label'],request=r,script=script,stdin=via['stdin'],returncode=run.returncode,stdout=run.stdout,stderr=run.stderr));print('via/copied-metal CAP reference native NaN captured',flush=True)
 result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents=parents,pi_gdb_commands=PI_COMMANDS,coupled_gdb_commands=COUPLED_COMMANDS,geometry_observer=SNAPSHOT,tap=TAP,reference=description or 'Unchanged original full COPY/RENAME/BEFRIEND/spatial edits followed by Pi2/CALCTRANS/2PORT, with selected copied windings in multi-object scenes, including a VIA copied onto a conductor metal. Read-only completed geometry snapshot, model/scattering/resonance/node observers and nonnumerical sprintf observer. Literal original CLI CAP with the unconverted VIA reference returns NaN totals and is retained separately. All selected outcomes retained.',cases=records,cap_reference_failures=cap_reference_failures)
 with gzip.GzipFile(str(ROOT/'tests/fixtures'/f'{output_name}.json.gz'),'wb',mtime=0)as out:out.write((json.dumps(result,separators=(',',':'),allow_nan=False)+'\n').encode())

if __name__=='__main__':main()
