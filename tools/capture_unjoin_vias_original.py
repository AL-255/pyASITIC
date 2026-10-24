"""Read-only via-stamp boundaries in actual split-device model commands."""
import argparse,gzip,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]
COMMANDS=r'''
set pagination off
set confirm off
set environment TERM dumb
set environment INPUTRC /dev/null
python
import gdb,struct,json
gdb.Breakpoint('*0x80657b8',internal=True)
end
run -g -t process.tek -x input.asit < answers.txt
python
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def u32(a):return struct.unpack('<I',mem(a,4))[0]
def i32(a):return struct.unpack('<i',mem(a,4))[0]
assert int(gdb.parse_and_eval('$pc'))==0x80657b8
esp=int(gdb.parse_and_eval('$esp'));finish=u32(esp);descriptor=u32(esp+4);ctx=u32(esp+8)
data=u32(descriptor);n=i32(descriptor+12);stride=i32(descriptor+20)
assert 0<n<=256 and stride>=n and i32(ctx+16)==n
indices=[i32(u32(ctx+44)+4*i)for i in range(i32(ctx+40))]
def matrix():return b''.join(mem(data+(j*stride+i)*16,16)for j in range(n)for i in range(n)).hex()
def cells():return [dict(index=k,address=data+(k*stride+k)*16,words=mem(data+(k*stride+k)*16,16).hex())for k in indices]
control=int(gdb.parse_and_eval('$fctrl'));before=matrix();cell_before=cells();segments=[];s=u32(u32(ctx)+0xa8)
while s:segments.append(mem(s,0xf0).hex());s=u32(s+0xec)
gdb.Breakpoint('*'+hex(finish),temporary=True,internal=True)
gdb.execute('continue',to_string=True)
assert int(gdb.parse_and_eval('$pc'))==finish
result=dict(n=n,stride=stride,descriptor=mem(descriptor,24).hex(),indices=indices,segments=segments,before=before,after=matrix(),cell_before=cell_before,cell_after=cells(),control_before=control,control_after=int(gdb.parse_and_eval('$fctrl')),return_status=int(gdb.parse_and_eval('$eax'))&255)
gdb.Breakpoint('*0x8053e00',temporary=True,internal=True)
gdb.execute('continue',to_string=True)
assert int(gdb.parse_and_eval('$pc'))==0x8053e00
esp=int(gdb.parse_and_eval('$esp'));node_n=u32(esp+12);cap=u32(esp+4);ind=u32(esp+8)
assert node_n==n
result['node']=dict(size=node_n,cap_address=cap,ind_address=ind,capacitance=mem(cap,16*n*n).hex(),inductance=mem(ind,16*n*n).hex(),control=int(gdb.parse_and_eval('$fctrl')))
open('vias.json','w').write(json.dumps(result))
end
kill
quit
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args();original=a.reference/'run/asitic.linux.2.2'
    for path,digest in((original,ORIGINAL_SHA256),(a.reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    parent=ROOT/'tests/fixtures/unjoin_sessions_original.json.gz';f=json.loads(gzip.decompress(parent.read_bytes()));cases=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-unjoin-vias-')as directory:
        for c in f['cases']:
            if c['label']not in('balun/head/pi2','balun/head-tail/calctrans'):continue
            work=Path(directory)/str(len(cases));work.mkdir()
            for name,value in(('process.tek',c['request']['technology']),('input.asit',c['script']),('answers.txt',c['stdin']),('capture.gdb',COMMANDS)):(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'vias.json').exists()or'Python Exception'in run.stderr:raise RuntimeError(run.stdout[-1800:]+run.stderr[-1200:])
            result=json.loads((work/'vias.json').read_text());cases.append(dict(label=c['label'],stdout=run.stdout,stderr=run.stderr,**result));print(c['label'],'n',result['n'],'stride',result['stride'],'via indices',result['indices'],flush=True)
    result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),gdb_commands=COMMANDS,reference='Read-only entry/return of the first actual original add_via_impedance call at 0x80657b8 in each selected unchanged UNJOIN model script, followed by the actual first node-solver input boundary. Defined n-by-n matrix, via target cells including out-of-domain diagonal indices, input chains, later CAP/inductive arrays and control words are retained. Observer terminates at node entry; full native outcomes are captured separately.',cases=cases)
    with gzip.GzipFile(str(ROOT/'tests/fixtures/unjoin_vias_original.json.gz'),'wb',mtime=0)as stream:stream.write((json.dumps(result,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
