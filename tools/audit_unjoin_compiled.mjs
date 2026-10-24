// Strict native node-CAP comparison. Observed alias replay is diagnostic only.
import{readFileSync,writeFileSync}from'node:fs';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
for(const name of['unjoin_sessions_original','unjoin_vias_original'])py.FS.writeFile('/'+name+'.json.gz',readFileSync(new URL('../tests/fixtures/'+name+'.json.gz',import.meta.url)));
const result=JSON.parse(py.runPython(`
import copy,gzip,hashlib,json,struct
from reasitic import Technology
from reasitic.bridge import _shapes,_mesh,_frequency
from reasitic.solver import discretize
from reasitic.potential import solve_capacitance
from reasitic.network import _join_for_pads
from reasitic.retained_scalar import Real as R
from reasitic.vias import stamp
parent=open('/unjoin_sessions_original.json.gz','rb').read()
sessions=json.loads(gzip.decompress(parent));fixture=json.loads(gzip.decompress(open('/unjoin_vias_original.json.gz','rb').read()))
assert hashlib.sha256(parent).hexdigest()==fixture['parent_sha256']
differences=[];cases=[];words=0
for c in fixture['cases']:
    r=next(s['request']for s in sessions['cases']if s['label']==c['label']);tech=Technology.from_text(r['technology']);shapes=_shapes(r,tech);mesh=_mesh(r,tech);freq=_frequency(r)
    length=mesh['length_cell'];cap_length=mesh['capacitance_length_cell'];cap_width=mesh['capacitance_width_cell']
    boundary=None
    if r['action']=='pi2':
        shape=discretize(shapes[r['winding']],cap_length,length)
        result=solve_capacitance(shape,tech,freq,length_cell=cap_length,width_cell=cap_width)
    else:
        a,b=(discretize(shapes[r[key]],cap_length,length)for key in('first_winding','second_winding'))
        boundary=sum(s.metal<len(tech.metals)for s in a.segments);b.segments.reverse();shape=_join_for_pads(a,b)
        result=solve_capacitance(shape,tech,freq,ground=shape,length_cell=cap_length,width_cell=cap_width)
    cap=result['matrix'];n=len(cap);assert n==c['n']==c['node']['size']
    if boundary is not None:cap[boundary][boundary][0]=float(R(1e15)+R(cap[boundary][boundary][0]));cap[boundary][boundary][1]+=0.
    actual=b''.join(struct.pack('<2d',*cap[i][j])for j in range(n)for i in range(n));native=bytes.fromhex(c['node']['capacitance']);words+=len(actual)//8
    for at in range(0,len(actual),8):
        if actual[at:at+8]!=native[at:at+8]:differences.append(dict(label=c['label'],row=at//16%n,column=at//16//n,component=at//8%2,actual=actual[at:at+8].hex(),original=native[at:at+8].hex()))
    # Use only the actually observed address relationship for this diagnostic.
    # No such mapping or selected-case correction enters the runtime.
    replay=bytearray(actual);aliases=[]
    via_records=[bytes.fromhex(s)for s in c['segments']if struct.unpack_from('<i',bytes.fromhex(s),0xdc)[0]>=len(tech.metals)]
    for s,k,before,after in zip(via_records,c['indices'],c['cell_before'],c['cell_after']):
        if k<n:continue
        offset=after['address']-c['node']['cap_address'];assert 0<=offset<=len(actual)-16 and offset%16==0
        assert actual[offset:offset+16].hex()==before['words']
        via=tech.vias[struct.unpack_from('<i',s,0xdc)[0]-len(tech.metals)];start,end=(struct.unpack_from('<d',s,o)[0]for o in(16,40));nx,ny=struct.unpack_from('<2i',s,0xe0);z=struct.unpack_from('<2d',actual,offset)
        value=stamp([[freq,start,end,via.width,via.resistance,nx,ny,*z]])[0];stored=struct.pack('<2d',value.real,value.imag);assert stored.hex()==after['words'];replay[offset:offset+16]=stored
        aliases.append(dict(via_index=k,row=offset//16%n,column=offset//16//n))
    cases.append(dict(label=c['label'],size=n,observed_aliases=aliases,observed_alias_replay_exact=bytes(replay)==native))
json.dumps(dict(capacitance_words=words,differences=differences,cases=cases))
`));
if(process.argv[3])writeFileSync(process.argv[3],JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result));process.exitCode=result.differences.length?1:0;
