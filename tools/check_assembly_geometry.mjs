// Intact original complete assembly and polygon stores through real Pyodide.
import {readFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import {installNumericalKernels} from "../web/numeric-kernels.mjs";
const {loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
for(const [key,name]of [["assembly_text","impedance_original"],["polygon_text","polygon_original"]])py.globals.set(key,readFileSync(new URL(`../tests/fixtures/${name}.json`,import.meta.url),"utf8"));
py.runPython(`
import json,struct
from array import array
from reasitic.impedance import assemble,_compiled_assembly
from reasitic.polygon import vertices,_compiled_polygon
from reasitic.mutual_kernel import mesh_mutual
assert _compiled_assembly is not None and _compiled_polygon is not None
components=0;count=0
for c in json.loads(assembly_text)['cases']:
 wires=[struct.unpack('<8d',bytes.fromhex(r['wire_bits']))for r in c['records']]
 metadata=[(r['sheet_resistance'],r['thickness_count'])for r in c['records']]
 pairs=[struct.unpack('<d',bytes.fromhex(v))[0]for v in c['mutual_bits']]
 # These actual-original mesh inputs also independently check the existing
 # unscaled pair kernel, before testing the consumed matrix assembly stores.
 packed=b''.join(bytes.fromhex(r['wire_bits'])for r in c['records']);native=mesh_mutual(packed)
 for i,bits in enumerate(c['mutual_bits']):assert struct.pack('<d',native[3*i+1]).hex()==bits
 saved=repr((wires,metadata,pairs));a=assemble(wires,metadata,pairs,c['frequency']);n=c['n']
 actual=b''.join(struct.pack('<dd',a[i][j].real,a[i][j].imag)for j in range(n)for i in range(j+1))
 assert actual.hex()==c['upper_bits'],('Original upper impedance assembly',c['fixture'],c['index'],c.get('mesh'))
 assert saved==repr((wires,metadata,pairs))
 for i in range(n):
  for j in range(n):assert a[i][j]==a[j][i]
 components+=n*(n+1);count+=1
print(f'{count} complete original upper impedance matrices / {components} exact binary64 components; native mesh pairs, symmetry reconstruction and immutable inputs passed.')
components=0;count=0
for c in json.loads(polygon_text)['cases']:
 config=c['config'].copy();rows=vertices(*config)
 assert config==c['config'] and len(rows)==len(c['rows'])
 for row,expected in zip(rows,c['rows']):assert struct.pack('<12d',*row).hex()==expected,('Original polygon stores',c['label'])
 count+=1;components+=12*len(rows)
print(f'{count} complete original polygon creators / {components} exact primary/outer/inner XY components passed.')
for w,p,o in [(array('d',[0.])*9,array('d'),array('d',[0.])*2),(array('d',[0.])*10,array('d',[0.]),array('d',[0.])*2)]:
 try:_compiled_assembly(w,p,o,1e9)
 except Exception:pass
 else:raise AssertionError('Invalid impedance buffers accepted')
for config,output in [(array('d',[0.])*5,array('d',[0.])*12),(array('d',[100.,6.,3.,2.,1.,0.]),array('d',[0.]))]:
 try:_compiled_polygon(config,output)
 except Exception:pass
 else:raise AssertionError('Invalid polygon buffers accepted')
`);
