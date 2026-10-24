"""Capture complete unchanged-original paired CALCTRANS/2PORTTRANS SI stores."""
import argparse,hashlib,json,os,re,struct,subprocess,tempfile
from pathlib import Path
from capture_transformer import TAP
from capture_paired_original import COMMANDS as GEOMETRY_COMMANDS
from capture_impedance_original import COMMANDS as ASSEMBLY_COMMANDS
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]
COMMANDS=r'''
set pagination off
set confirm off
set environment TERM dumb
set environment INPUTRC /dev/null
set environment LD_PRELOAD TAP_PATH
handle SIGQUIT nostop noprint pass
python
import gdb,struct,json
records=[];nodes=[]
def memory(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def u32(a):return struct.unpack('<I',memory(a,4))[0]
def ports():return [memory(a,8).hex()for a in(0x80d8da8,0x80d8db0,0x80d8db8,0x80d8dc0,0x80d8dd8,0x80d8de0,0x80d8de8,0x80d8df0)]
class Return(gdb.Breakpoint):
 def __init__(self,ret,y,cw):
  super().__init__('*'+hex(ret),temporary=True,internal=True);self.y=y;self.cw=cw
 def stop(self):
  records.append(dict(Y=self.y,S=[memory(a,8).hex()for base in(0x80d8d58,0x80d8d28,0x80d8d48,0x80d8d18)for a in(base,base+8)],control_before=self.cw,control_after=int(gdb.parse_and_eval('$fctrl'))));return False
class Entry(gdb.Breakpoint):
 def stop(self):
  Return(u32(int(gdb.parse_and_eval('$esp'))),ports(),int(gdb.parse_and_eval('$fctrl')));return False
class Nodes(gdb.Breakpoint):
 def stop(self):
  esp=int(gdb.parse_and_eval('$esp'));n=u32(esp+12)
  assert 0<n<=256
  nodes.append(dict(size=n,capacitance=memory(u32(esp+4),16*n*n).hex(),inductance=memory(u32(esp+8),16*n*n).hex()))
  return False
Nodes('*0x8053e00',internal=True)
Entry('*0x8087d14',internal=True)
end
run -g -t process.tek -x input.asit < answers.txt
python
signal=0
if gdb.selected_inferior().pid:
 signal=int(gdb.parse_and_eval('$_siginfo.si_signo'));gdb.execute('kill',to_string=True)
open('scattering.json','w').write(json.dumps(dict(records=records,nodes=nodes,signal=signal)))
end
quit
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);args=parser.parse_args()
    ref=args.reference.resolve();original=ref/'run/asitic.linux.2.2';legacy=ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,want in [(original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
    parent=ROOT/'tests/fixtures/paired_original.json';f=json.loads(parent.read_text());technology=f['technology']
    for key,value in [('chipx',256),('chipy',256),('fftx',128),('ffty',128)]:technology=re.sub(rf'(?im)^(\s*{key}\s*=\s*)[\d.]+',rf'\g<1>{value}',technology)
    records=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-paired-models-')as d:
        root=Path(d);(root/'tap.cpp').write_text(TAP)
        subprocess.run(['g++','-m32','-O2','-fPIC','-shared','-nostdlib','-fno-builtin',str(root/'tap.cpp'),'/lib/i386-linux-gnu/libc.so.6','-o',str(root/'tap.so')],check=True)
        for i,index in enumerate([0,45,64,87,91,93]):
            c=f['cases'][index];p=dict(c['parameters'],x=40,y=40);frequency=[.1234567,2.34567891,1.23456789,1.987654321,2.12345678,1][i];eddy=i in(1,4);explicit=i in(1,3);termination=50 if i==1 else 0
            creation=c['script'].replace(':XORG=12.345:YORG=23.456',':XORG=40:YORG=40');answers=c['stdin'].replace('12.3456789 23.456789','40 40')
            if c['native_keyword']and'XORG'not in creation:creation=creation.rstrip()+':XORG=40:YORG=40\n'
            first,second=[w['name']for w in c['windings']];text=format(frequency,'.17g');suffix=f' {first} {termination}'if explicit else''
            script='CELL 1000 1000 1000\nCCELL 1000 1000\n'+f'EDDY {"ON"if eddy else"OFF"}\n'+creation+f'CALCTRANS {first} {second} {text}{suffix}\n2PORTTRANS {first} {second} {text} {text} 1 Y RECT y.out{suffix}\n2PORTTRANS {first} {second} {text} {text} 1 S RECT s.out{suffix}\n'
            work=root/str(i);work.mkdir()
            for name,value in [('process.tek',technology),('input.asit',script),('answers.txt',answers),('capture.gdb',COMMANDS.replace('TAP_PATH',str(root/'tap.so'))) ]:(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=180)
            if run.returncode or not(work/'scattering.json').exists():raise RuntimeError(f'Original paired session {i} failed: '+run.stdout[-1800:]+run.stderr[-900:])
            scatter=json.loads((work/'scattering.json').read_text());raw=(work/'transformer-raw.out').read_bytes()if(work/'transformer-raw.out').exists()else b''
            definition=dict(kind=c['kind'],parameters=p,native_keyword=c.get('native_keyword',False),native_interactive=c.get('native_interactive',False))
            request=dict(action='calctrans',**definition,first_winding=0,second_winding=1,technology=technology,frequency_ghz=frequency,eddy=eddy,termination_ohm=termination,mesh={key:1000 for key in ['length_cell','width_cell','thickness_cell','capacitance_length_cell','capacitance_width_cell']})
            if explicit:request['ground']=dict(definition,winding=0)
            if scatter['signal']or len(raw)<23*8 or not scatter['records']:raise RuntimeError(f'Original paired session {i} produced no full model: '+run.stdout[-1800:])
            for s in scatter['records']:
                if s['control_before']!=0x37f or s['control_after']!=0x37f:raise RuntimeError('Original control word changed')
            geometry_commands=GEOMETRY_COMMANDS.replace('ENTRY',hex(0x80576d4 if c['kind']=='transformer'else 0x8059854)).replace('KIND',repr(c['kind']))
            (work/'geometry.gdb').write_text(geometry_commands)
            geo=subprocess.run(['gdb','-q','-batch','-x','geometry.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if geo.returncode or not(work/'paired.json').exists():raise RuntimeError('Missing original session geometry: '+geo.stdout[-1000:])
            geometry=json.loads((work/'paired.json').read_text())
            (work/'assembly.gdb').write_text(ASSEMBLY_COMMANDS)
            assembly_run=subprocess.run(['gdb','-q','-batch','-x','assembly.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=180)
            if assembly_run.returncode or not(work/'assembly.json').exists():raise RuntimeError('Missing original assembly: '+assembly_run.stdout[-1200:])
            assembly=json.loads((work/'assembly.json').read_text())
            records.append(dict(request=request,parent_case=index,script=script,stdin=answers,stdout=run.stdout,geometry=geometry,assembly=assembly,node_events=scatter['nodes'],raw_output_bits=[raw[j:j+8].hex()for j in range(0,23*8,8)],scattering=scatter['records'][-1],scattering_events=scatter['records']))
            print(f'Original paired electrical {i}: {c["label"]}',flush=True)
    output=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),tap=TAP,gdb_commands=COMMANDS,reference='Unchanged original paired creation followed by complete CALCTRANS and 2PORTTRANS commands. Data-only sprintf tap captures the original SI Y/Z/model stores before unit formatting, and data-only scattering entry/return observers capture every original S store; no numerical instructions or input records patched.',cases=records)
    (ROOT/'tests/fixtures/paired_sessions_original.json').write_text(json.dumps(output,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
