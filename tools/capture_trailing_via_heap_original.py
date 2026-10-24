"""Original array lifetimes and trailing-via targets across sizes and meshes."""
import argparse,copy,gzip,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]
COMMANDS=r'''
set pagination off
set confirm off
set environment TERM dumb
set environment INPUTRC /dev/null
handle SIGQUIT nostop noprint pass
python
import gdb,struct,json
active=False;events=[];pending={};returns={};matrices={};via=None;node=None;cap_frame=None;cap_output=None;contact_groups=[]
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def reg(k):return int(gdb.parse_and_eval('$'+k))&0xffffffff
def u32(a):return struct.unpack('<I',mem(a,4))[0]
def i32(a):return struct.unpack('<i',mem(a,4))[0]
def optional_mem(a,n):
 try:return mem(a,n).hex()
 except gdb.MemoryError:return None
def matrix(descriptor):
 data=u32(descriptor);n=i32(descriptor+12);stride=i32(descriptor+20)
 assert 0<n<=1024 and stride>=n
 return dict(data=data,size=n,stride=stride,descriptor=mem(descriptor,24).hex())
class Observe(gdb.Breakpoint):
 def stop(self):
  global active,cap_frame,cap_output,via,node
  pc=reg('pc');esp=reg('esp');caller=u32(esp)
  if pc==0x8052ec7:
   if cap_frame is not None:return False
   cap_frame=reg('ebp');cap_output=u32(cap_frame+8);active=True
   group=u32(0x80ce9a4)
   while group:
    contacts=[];contact=u32(group+0x80)
    while contact:contacts.append(contact);contact=u32(contact+0x38)
    contact_groups.append(dict(address=group,contacts=contacts));group=u32(group+0x84)
   events.append(dict(kind='scope',contacts=i32(cap_frame-0xbc),groups=i32(cap_frame-0xb4),control=reg('fctrl')))
  elif not active:return False
  elif pc in(0x804ab74,0x804adb4):
   item=dict(kind='allocate',allocator='array'if pc==0x804ab74 else'scalar',request=u32(esp+4),caller=caller);events.append(item);pending.setdefault(caller,[]).append(item)
   if caller not in returns:returns[caller]=Observe('*'+hex(caller),internal=True)
  elif pc in(0x804ac74,0x804ad84):
   pointer=u32(esp+4);events.append(dict(kind='free',allocator='array'if pc==0x804ac74 else'scalar',address=pointer,caller=caller,chunk_size=(u32(pointer-4)&~7)if pointer else None))
  elif pc in(0x8052edb,0x805314d,0x805329c,0x8053480):
   label,descriptor={0x8052edb:('cap_full',cap_frame-0x40),0x805314d:('cap_reduced',cap_frame-0x60),0x805329c:('cap_folded',cap_frame-0x8c),0x8053480:('cap_output',cap_output)}[pc]
   matrices[label]=matrix(descriptor);events.append(dict(kind='matrix',label=label,**matrices[label]))
  elif pc==0x80650d4:
   matrices['ind_full']=matrix(u32(esp+4));events.append(dict(kind='matrix',label='ind_full',**matrices['ind_full']))
  elif pc==0x80657b8:
   if via is not None:return False
   descriptor=u32(esp+4);ctx=u32(esp+8);out=matrix(descriptor);n=out['size'];data=out['data'];stride=out['stride'];indices=[i32(u32(ctx+44)+4*i)for i in range(i32(ctx+40))]
   segments=[];segment_addresses=[];shape=u32(ctx);s=u32(shape+0xa8)
   while s:segment_addresses.append(s);segments.append(mem(s,0xf0).hex());s=u32(s+0xec)
   via=dict(matrix=out,indices=indices,shape_address=shape,segment_addresses=segment_addresses,segments=segments,cells=[dict(index=k,address=data+(k*stride+k)*16,before=optional_mem(data+(k*stride+k)*16,16))for k in indices],writes=[],control_before=reg('fctrl'))
   events.append(dict(kind='via_entry',**out,indices=indices));Observe('*'+hex(caller),internal=True,temporary=True)
  elif pc==0x8065930:
   item=dict(kind='via_write',ordinal=i32(reg('ebp')-0x20),index=i32(reg('ebp')-0x30),address=reg('edi'),before=optional_mem(reg('edi'),16),resistance_extended=bytes(gdb.parse_and_eval('$st0').bytes).hex())
   via['writes'].append(item);events.append(item)
  elif pc==0x806593f:
   item=via['writes'][-1];item['after']=optional_mem(reg('edi'),16);events.append(dict(kind='via_stored',index=item['index'],address=reg('edi'),after=item['after']))
  elif pc==0x8053e00:
   n=u32(esp+12);assert 0<n<=1024;cap=u32(esp+4);ind=u32(esp+8)
   node=dict(size=n,cap_address=cap,ind_address=ind,capacitance=mem(cap,16*n*n).hex(),inductance=mem(ind,16*n*n).hex(),control=reg('fctrl'));active=False;return True
  elif pc in pending and pending[pc]:pending[pc].pop()['address']=reg('eax')
  elif via is not None and 'return_status'not in via:
   via['return_status']=reg('eax')&255;via['control_after']=reg('fctrl')
   for cell in via['cells']:cell['after']=optional_mem(cell['address'],16)
   events.append(dict(kind='via_return',return_status=via['return_status']))
  return False
for address in(0x8052ec7,0x804ab74,0x804adb4,0x804ac74,0x804ad84,0x8052edb,0x805314d,0x805329c,0x8053480,0x80650d4,0x80657b8,0x8065930,0x806593f,0x8053e00):Observe('*'+hex(address),internal=True)
end
run -g -t process.tek -x input.asit < answers.txt
python
signal=0
if node is None and gdb.selected_inferior().pid:
 try:signal=int(gdb.parse_and_eval('$_siginfo.si_signo'))
 except gdb.error:pass
result=dict(events=events,contact_groups=contact_groups,matrices=matrices,via=via,node=node,signal=signal,pending=sum(map(len,pending.values())))
open('heap.json','w').write(json.dumps(result))
if gdb.selected_inferior().pid:gdb.execute('kill',to_string=True)
end
quit
'''


def jobs():
    parent=ROOT/'tests/fixtures/square_original.json';technology=json.loads(parent.read_text())['technology']
    for key,value in(('chipx',256),('chipy',256),('fftx',128),('ffty',128)):
        technology=re.sub(rf'(?im)^(\s*{key}\s*=\s*)[\d.]+',rf'\g<1>{value}',technology)
    configurations=[('square',n,240,6,1,8)for n in(1,2,3,4,5,6,7,8,9,10,12,16,24,32,40,48,64)]
    # Preserve every exploratory pilot, including the narrow-wire cases that
    # abort on the complete unobserved run. These are additional inputs, not
    # replacements for any independently selected size or mesh.
    configurations += [('pilot-width3',1,160,3,2,40)]
    configurations += [('pilot-boundary',n,256,6,1,0)for n in(1,2,3)]
    for label,n,length,conductor_width,spacing,origin in configurations:
        p=dict(name='A',length=length,height=length,width=conductor_width,spacing=spacing,turns=n/4,metal='M4',exit_metal='M3',angle=0,phase=1,x=origin,y=origin)
        creation=f'SQUARE NAME=A:LEN={length}:WID={length}:W={conductor_width}:S={spacing}:N={n/4}:METAL=M4:EXIT=M3:ORIENT=0:PHASE=1:XORG={origin}:YORG={origin}\n'
        for variant,width,cap_width in(('coarse',1000,1000),('filaments',1,1000),('contacts',1000,2)):
            mesh=dict(length_cell=1000,width_cell=width,thickness_cell=1000,capacitance_length_cell=1000,capacitance_width_cell=cap_width)
            r=dict(action='pi2',kind='square',parameters=p,native_keyword=True,native_mesh=True,technology=technology,frequency_ghz=.25,frequency_hz=250e6,eddy=False,winding=0,mesh=mesh,edits=[dict(command='UNJOIN',winding=0,index=n+1,name='tail')])
            prefix=f'CELL 1000 {width} 1000\nCCELL 1000 {cap_width}\nEDDY OFF\n'+creation
            script=prefix+f'UNJOIN A {n+1} TAIL\nGEOM A\nPI2 A .25\n2PORT A .25 .25 1 S RECT SLOW s.out\n'
            yield dict(label=f'{label}/{n}/{variant}',parent=parent,request=copy.deepcopy(r),script=script,stdin='quit\n',nominal_conductors=n,variant=variant)
    parent=ROOT/'tests/fixtures/unjoin_sessions_original.json.gz'
    for c in json.loads(gzip.decompress(parent.read_bytes()))['cases']:
        if c['label']in('balun/head/pi2','balun/head-tail/calctrans'):
            yield dict(label=c['label'],parent=parent,request=c['request'],script=c['script'],stdin=c['stdin'],variant='existing')


def main(*,commands=COMMANDS,fixture_name="trailing_via_heap_original.json.gz",extra_metadata=None,job_factory=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);p.add_argument('--limit',type=int);a=p.parse_args();original=a.reference/'run/asitic.linux.2.2'
    for path,digest in((original,ORIGINAL_SHA256),(a.reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    cases=[];prior=ROOT/'tests/fixtures/trailing_via_heap_mixed_cache_original.json.gz';parents={prior.name:hashlib.sha256(prior.read_bytes()).hexdigest()}
    def manifest(values):return {name:dict(size=len(data),sha256=hashlib.sha256(data).hexdigest())for name,data in sorted(values.items())}
    with tempfile.TemporaryDirectory(prefix='pyasitic-trailing-heap-')as directory:
        for ordinal,c in enumerate((jobs if job_factory is None else job_factory)()):
            if a.limit is not None and ordinal>=a.limit:break
            parent=c.pop('parent');parents[parent.name]=hashlib.sha256(parent.read_bytes()).hexdigest();case_root=Path(directory)/str(ordinal);case_root.mkdir();cold_cache={}
            for mode in('cold','warm'):
                work=case_root/mode;work.mkdir();initial={name:value.encode()for name,value in(('process.tek',c['request']['technology']),('input.asit',c['script']),('answers.txt',c['stdin']),('capture.gdb',commands))}
                cache={}if mode=='cold'else cold_cache.copy();initial.update(cache)
                for name,value in initial.items():(work/name).write_bytes(value)
                env=dict(os.environ,LD_LIBRARY_PATH=a.library_path,TERM='dumb',INPUTRC='/dev/null')
                plain=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],cwd=work,env=env,input=c['stdin'],capture_output=True,text=True,start_new_session=True,timeout=180)
                scattering=(work/'s.out').read_text()if(work/'s.out').exists()else None
                produced_cache={p.name:p.read_bytes()for p in work.glob('*.dat')}
                if mode=='cold':cold_cache=produced_cache.copy()
                # Restore exactly the same files in the same cwd before GDB.
                # A plain cold run must not silently warm the observed run.
                for path in work.iterdir():
                    if path.is_file()and path.name not in initial:path.unlink()
                for name,value in initial.items():(work/name).write_bytes(value)
                assert {p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in work.iterdir()if p.is_file()}=={name:hashlib.sha256(value).hexdigest()for name,value in initial.items()}
                run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=env,capture_output=True,text=True,start_new_session=True,timeout=180)
                if run.returncode or not(work/'heap.json').exists()or'Python Exception'in run.stderr:raise RuntimeError(c['label']+'/'+mode+run.stdout[-1800:]+run.stderr[-1800:])
                result=json.loads((work/'heap.json').read_text());cases.append(dict(c,cache_mode=mode,initial_cache=manifest(cache),cache_after_plain=manifest(produced_cache),initial_files=manifest(initial),stdout=run.stdout,stderr=run.stderr,plain=dict(returncode=plain.returncode,stdout=plain.stdout,stderr=plain.stderr,scattering_text=scattering),**result))
                print(c['label'],mode,'events',len(result['events']),'node',result['node']['size']if result['node']else None,'signal',result['signal'],'plain',plain.returncode,flush=True)
    result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents=parents,gdb_commands=commands,environment_overrides=dict(TERM='dumb',INPUTRC='/dev/null'),reference='Unchanged original scripts across independently chosen square sizes and meshes, both existing split-balun cases, and every exploratory pilot. Cold and warm disk-cache states are separate observations. Each plain/GDB pair starts with byte-identical files in the same cwd; warm data files are generated by the original cold plain run. Read-only scalar/array allocation/free events begin before CAP full-matrix construction; descriptors, via inputs/targets and first node inputs are retained. GDB runs stop at node input or fault, not command exit. The earlier warm-observer/cold-plain experiment is retained as a separately identified parent and is not treated as an identical-state comparison.',cases=cases)
    if extra_metadata:result.update(extra_metadata)
    with gzip.GzipFile(str(ROOT/'tests/fixtures'/fixture_name),'wb',mtime=0)as stream:stream.write((json.dumps(result,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
