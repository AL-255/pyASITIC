// Full contact matrices from original machine code, through the shipped Python transport.
import {readFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import assert from "node:assert/strict";
import {installNumericalKernels} from "../web/numeric-kernels.mjs";
const {loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
py.runPython(`
import json,hashlib,struct,math,copy
from reasitic.potential import Contact
from reasitic.contact_kernel import contact_matrix,_compiled_contact_pair
assert _compiled_contact_pair is not None
def contact_probe(payload):
    c=json.loads(payload);original=copy.deepcopy(c)
    nx,ny=c["nx"],c["ny"];cells=max((nx+1)*(ny+1),nx*(nx+1)+ny+1)
    saved={};pairs={(p["low"],p["high"]):p for p in c["pairs"]}
    def packed(values):return b"".join(struct.pack("<dd",z.real,z.imag) for z in values)
    def scaled(value,scale):return math.copysign(math.inf,value if value else 1) if scale=="inf" else value*scale
    def get_table(low,high):
        p=pairs[low,high];seed=p["seed"]
        values=[complex(scaled((i*8191+seed*17)%65521-32760,c["scale"][0]),scaled((i*257+seed*31)%4093-2046,c["scale"][1])) for i in range(2*nx+2*ny+cells)]
        assert hashlib.sha256(packed(values)).hexdigest()==p["input_sha256"],"Contact table input bits differ"
        tables=(values[:2*nx],values[2*nx:2*nx+2*ny],values[2*nx+2*ny:]);saved[low,high]=tables
        return tables
    result=contact_matrix([Contact(*v) for v in c["contacts"]],nx,ny,c["width"],c["height"],c["metals"],[complex(*z) for z in c["coefficients"]],c["depths"],get_table)
    assert c==original,"Contact metadata mutated"
    for pair,tables in saved.items():
        assert hashlib.sha256(packed(z for t in tables for z in t)).hexdigest()==pairs[pair]["input_sha256"],"Input tables mutated"
    if c.get("digest_only"):return json.dumps(dict(sha256=hashlib.sha256(packed(z for row in result for z in row)).hexdigest()))
    return json.dumps([[struct.pack("<dd",z.real,z.imag).hex() for z in row] for row in result])
`);
function nativeJSON(value){
  if(typeof value==="number"&&Object.is(value,-0))return "-0.0";
  if(Array.isArray(value))return "["+value.map(nativeJSON).join(",")+"]";
  if(value&&typeof value==="object")return "{"+Object.entries(value).map(([k,v])=>JSON.stringify(k)+":"+nativeJSON(v)).join(",")+"}";
  return JSON.stringify(value);
}
const cases=JSON.parse(readFileSync(new URL("../tests/fixtures/contact_potential.json",import.meta.url)));
const probe=py.globals.get("contact_probe");let components=0;
for(const [index,c] of cases.cases.entries()){
  const actual=JSON.parse(probe(nativeJSON(c)));
  if(c.digest_only){assert.equal(actual.sha256,c.output_sha256,`Complete original ${c.contacts.length}-contact matrix bits`);components+=2*c.contacts.length**2;continue;}
  c.output.forEach((row,i)=>row.forEach((z,j)=>z.forEach((expected,k)=>{
    const bytes=Buffer.from(actual[i][j],"hex"),value=bytes.readDoubleLE(8*k);
    if(expected==="nan")assert.ok(Number.isNaN(value),`Native NaN classification ${index}`);
    else if(expected==="inf"||expected==="-inf")assert.equal(value,expected==="inf"?Infinity:-Infinity);
    else{const target=Buffer.alloc(8);target.writeDoubleLE(expected);assert.equal(bytes.subarray(8*k,8*k+8).toString("hex"),target.toString("hex"),`Original contact bits case ${index} [${i},${j},${k}]`);}
    components++;
  })));
}
assert.equal(components,cases.components);
probe.destroy();
console.log(`${cases.cases.length} original-binary contact matrices passed (${components} output components, finite bits and nonfinite classifications), including complete 256-contact output.`);
// Exercise production coefficient/table generation as well as the isolated
// contact arithmetic. Keep the existing native snapshot tolerances unchanged.
py.globals.set("potential_fixtures",readFileSync(new URL("../tests/fixtures/potential.json",import.meta.url),"utf8"));
py.runPython(`
from reasitic import Technology,build
from reasitic.potential import solve_capacitance
for case in json.loads(potential_fixtures)["cases"]:
    technology=Technology.from_text(case["technology"])
    shape=build(case["kind"],technology=technology,**case["parameters"])
    ground=build("wire",technology=technology,**case["ground"]) if case["ground"] else None
    result=solve_capacitance(shape,technology,case["frequency_hz"],ground=ground,
        length_cell=case["length_cell"],width_cell=case["width_cell"],include_potential=True)
    for key,reference,floor in (("potential_matrix",case["potential"],1e-9),("matrix",case["matrix"],1e-16)):
        actual=result[key]
        assert len(actual)==len(reference),(case["kind"],key,"row count")
        for i,(row,expected_row) in enumerate(zip(actual,reference)):
            assert len(row)==len(expected_row),(case["kind"],key,"column count")
            for j,(z,expected_z) in enumerate(zip(row,expected_row)):
                for k,(value,expected) in enumerate(zip(z,expected_z)):
                    assert abs(value-expected)<=max(floor,abs(expected)*1e-8),(case["process"],case["kind"],case["frequency_hz"],key,i,j,k,value,expected)
`);
console.log("Eight production raw potential and reduced capacitance matrices passed unchanged native snapshot tolerances.");
