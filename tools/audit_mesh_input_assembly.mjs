// Strict stage audit for the complete captured native mesh input histories.
import{readFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
py.globals.set('fixture_text',gunzipSync(readFileSync(new URL('../tests/fixtures/mesh_inputs_original.json.gz',import.meta.url))).toString());
try{py.runPython(`
import json,struct
from reasitic.mutual_kernel import mesh_mutual
from reasitic.impedance import assemble
from reasitic.symmetric import factor_symmetric_upper,inverse_symmetric
from reasitic.reduction import sum_complex
fixture=json.loads(fixture_text);failures=[]
for index,c in enumerate(fixture['cases']):
 a=c['assembly'];wires=[struct.unpack('<8d',bytes.fromhex(r['wire_bits']))for r in a['records']]
 pairs=mesh_mutual(b''.join(struct.pack('<8d',*w)for w in wires));assert all(pairs[i]==0 for i in range(0,len(pairs),3))
 full=assemble(wires,[(r['sheet_resistance'],r['thickness_count'])for r in a['records']],list(pairs[1::3]),a['frequency'])
 actual=b''.join(struct.pack('<2d',full[i][j].real,full[i][j].imag)for j in range(a['n'])for i in range(j+1));expected=bytes.fromhex(a['upper_bits'])
 differences=[(i,struct.unpack('<d',actual[i:i+8])[0],struct.unpack('<d',expected[i:i+8])[0])for i in range(0,len(actual),8)if actual[i:i+8]!=expected[i:i+8]]
 print('Original mesh input assembly',index,'n',a['n'],'component differences',len(differences),differences[:8],flush=True)
 failures.extend((index,'assembly',*r)for r in differences)
 for e,following in zip(c['inversions']['events'][::2],c['inversions']['events'][1::2]):
  n=e['n'];matrix=[[0j]*n for _ in range(n)];raw=bytes.fromhex(e['input_bits']);offset=0
  for j in range(n):
   for i in range(j+1):matrix[i][j]=matrix[j][i]=complex(*struct.unpack_from('<2d',raw,offset));offset+=16
  factor,pivots=factor_symmetric_upper(matrix)
  for label,actual_matrix,expected in [('factor',factor,e['output_bits']),('inverse',inverse_symmetric(matrix),following['output_bits'])]:
   actual=b''.join(struct.pack('<2d',actual_matrix[i][j].real,actual_matrix[i][j].imag)for j in range(n)for i in range(j+1));expected=bytes.fromhex(expected)
   differences=[(i,struct.unpack('<d',actual[i:i+8])[0],struct.unpack('<d',expected[i:i+8])[0])for i in range(0,len(actual),8)if actual[i:i+8]!=expected[i:i+8]]
   print('Original mesh input',index,label,'n',n,'component differences',len(differences),differences[:8],'pivot differences',sum(a!=b for a,b in zip(pivots,e['pivots'])),flush=True)
   failures.extend((index,label,*r)for r in differences)
 if len(c['inversions']['events'])>2:
  upper=c['inversions']['events'][1];n=upper['n'];raw=bytes.fromhex(upper['output_bits']);matrix=[[0j]*n for _ in range(n)];offset=0
  for j in range(n):
   for i in range(j+1):matrix[i][j]=matrix[j][i]=complex(*struct.unpack_from('<2d',raw,offset));offset+=16
  counts=c['lmat']['counts'][0];groups=[];offset=0
  for w,t in zip(counts['width'],counts['thickness']):groups.append(range(offset,offset+w*t));offset+=w*t
  values=[];direct=[]
  for j,columns in enumerate(groups):
   for rows in groups[:j+1]:
    block=[matrix[r][col]for r in rows for col in columns];value=sum_complex(block);values.extend((value.real,value.imag));real=imag=0.
    for z in block:real+=z.real;imag+=z.imag
    direct.extend((real,imag))
  actual=struct.pack('<'+'d'*len(values),*values).hex();expected=c['inversions']['events'][2]['input_bits']
  differences=sum(actual[i:i+16]!=expected[i:i+16]for i in range(0,len(actual),16));baseline=struct.pack('<'+'d'*len(direct),*direct).hex()
  print('Original mesh reduction',index,'component differences',differences,'direct-binary64 differences',sum(baseline[i:i+16]!=expected[i:i+16]for i in range(0,len(baseline),16)),flush=True)
  if differences:failures.append((index,'reduction',actual,expected))
assert not failures,(len(failures),'original assembly/factor/inverse/reduction stores differ')
`);}catch(error){console.error(String(error));process.exit(1);}
