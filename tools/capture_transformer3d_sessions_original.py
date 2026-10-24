"""Capture raw 3D LMAT and coupled-model histories in the intact original CLI."""
import argparse,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
from capture_paired_sessions_original import COMMANDS as PAIRED_COMMANDS
from capture_transformer import TAP
ROOT=Path(__file__).resolve().parents[1]
COMMANDS=PAIRED_COMMANDS
LMAT_COMMANDS=r'''
set pagination off
set confirm off
set environment TERM dumb
set environment INPUTRC /dev/null
break *0x8064360
run -g -t process.tek -x input.asit < answers.txt
python
import gdb,struct,json
def memory(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def u32(a):return struct.unpack('<I',memory(a,4))[0]
matrices=[];entry=gdb.breakpoints()[0]
for index in range(2):
 assert int(gdb.parse_and_eval('$pc'))==0x8064360
 esp=int(gdb.parse_and_eval('$esp'));shape=u32(esp+4);d=u32(esp+8);ret=u32(esp)
 item=dict(name=memory(shape,80).split(b'\0')[0].decode('latin1'),frequency_bits=memory(esp+12,8).hex(),impedance=u32(esp+20)&255,control_before=int(gdb.parse_and_eval('$fctrl')))
 entry.enabled=False;gdb.Breakpoint('*'+hex(ret),temporary=True,internal=True);gdb.execute('continue',to_string=True)
 assert int(gdb.parse_and_eval('$pc'))==ret
 n=u32(d+12);stride=u32(d+20);data=u32(d);assert 0<n<=256 and stride>=n
 item.update(size=n,success=int(gdb.parse_and_eval('$eax'))&255,matrix_bits=b''.join(memory(data+16*j*stride,16*n)for j in range(n)).hex(),control_after=int(gdb.parse_and_eval('$fctrl')))
 matrices.append(item);entry.enabled=True
 if index==0:gdb.execute('continue',to_string=True)
open('lmat.json','w').write(json.dumps(matrices))
end
kill
quit
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);args=parser.parse_args()
    ref=args.reference.resolve();original=ref/'run/asitic.linux.2.2';legacy=ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,want in [(original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
    parent=ROOT/'tests/fixtures/transformer3d_original.json';f=json.loads(parent.read_text());technology=f['technology']
    for key,value in [('chipx',256),('chipy',256),('fftx',128),('ffty',128)]:technology=re.sub(rf'(?im)^(\s*{key}\s*=\s*)[\d.]+',rf'\g<1>{value}',technology)
    records=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-3d-models-')as d:
        root=Path(d);(root/'tap.cpp').write_text(TAP)
        subprocess.run(['g++','-m32','-O2','-fPIC','-shared','-nostdlib','-fno-builtin',str(root/'tap.cpp'),'/lib/i386-linux-gnu/libc.so.6','-o',str(root/'tap.so')],check=True)
        for i,index in enumerate([0,19,32,47,64,73]):
            c=f['cases'][index];p=dict(c['parameters'],x=40,y=40);frequency=[.1234567,2.34567891,1.23456789,1.987654321,2.12345678,1][i];eddy=i in(1,4);explicit=i in(1,3);termination=50 if i==1 else 0
            answers=c['stdin'].replace('12.3456789 23.456789','40 40');text=format(frequency,'.17g');suffix=f' P {termination}'if explicit else''
            script='CELL 1000 1000 1000\nCCELL 1000 1000\n'+f'EDDY {"ON"if eddy else"OFF"}\n3DMIRRORTRANS\nLMAT P {text} p.out\nLMAT S {text} s.out\n'+f'CALCTRANS P S {text}{suffix}\n2PORTTRANS P S {text} {text} 1 Y RECT y.out{suffix}\n2PORTTRANS P S {text} {text} 1 S RECT ports.out{suffix}\n'
            work=root/str(i);work.mkdir()
            for name,value in [('process.tek',technology),('input.asit',script),('answers.txt',answers),('capture.gdb',COMMANDS.replace('TAP_PATH',str(root/'tap.so'))) ]:(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=180)
            if run.returncode or not(work/'scattering.json').exists():raise RuntimeError(f'Original 3D model {i} failed: '+run.stdout[-1800:]+run.stderr[-1000:])
            (work/'lmat.gdb').write_text(LMAT_COMMANDS)
            lmat_run=subprocess.run(['gdb','-q','-batch','-x','lmat.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=180)
            if lmat_run.returncode or not(work/'lmat.json').exists():raise RuntimeError('Missing exact original LMAT returns: '+lmat_run.stdout[-1200:]+lmat_run.stderr[-1000:])
            matrices=json.loads((work/'lmat.json').read_text())
            raw=json.loads((work/'scattering.json').read_text());model=(work/'transformer-raw.out').read_bytes()if(work/'transformer-raw.out').exists()else b''
            if len(matrices)!=2:raise RuntimeError('Missing standalone LMAT returns')
            for event in matrices+raw['records']:
                if event['control_before']!=event['control_after']or event['control_before']!=0x37f:raise RuntimeError('Unexpected original control word')
            plain_work=work/'plain';plain_work.mkdir()
            for name,value in [('process.tek',technology),('input.asit',script)]:(plain_work/name).write_text(value)
            plain=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],cwd=plain_work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path,TERM='dumb',INPUTRC='/dev/null'),input=answers,capture_output=True,text=True,start_new_session=True,timeout=180)
            definition=dict(kind='transformer3d',parameters=p,native_interactive=True)
            request=dict(action='calctrans',**definition,first_winding=0,second_winding=1,technology=technology,frequency_ghz=frequency,eddy=eddy,termination_ohm=termination,mesh={key:1000 for key in ['length_cell','width_cell','thickness_cell','capacitance_length_cell','capacitance_width_cell']})
            if explicit:request['ground']=dict(definition,winding=0)
            lmat=[dict(request=dict(request,action='lmat',winding=j),**m)for j,m in enumerate(matrices)]
            records.append(dict(request=request,parent_case=index,script=script,stdin=answers,stdout=run.stdout,lmat=lmat,node_events=raw['nodes'],signal=raw['signal'],stderr=run.stderr,plain_returncode=plain.returncode,plain_stdout=plain.stdout,plain_stderr=plain.stderr,raw_output_bits=[model[j:j+8].hex()for j in range(0,min(len(model),23*8),8)],scattering=raw['records'][-1]if raw['records']else None,scattering_events=raw['records']))
            print(f'Original 3D electrical {i}: {c["label"]}',flush=True)
    out=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),tap=TAP,gdb_commands=COMMANDS,lmat_gdb_commands=LMAT_COMMANDS,reference='Unmodified original prompt creation, two standalone LMAT commands and complete CALCTRANS/2PORTTRANS history. Original driver return descriptors provide raw matrices; a data-only sprintf observer and node/scattering entry/return observers preserve original raw SI model stores. No numerical instructions or input data patched; all original nonfinite histories retained.',cases=records)
    (ROOT/'tests/fixtures/transformer3d_sessions_original.json').write_text(json.dumps(out,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
