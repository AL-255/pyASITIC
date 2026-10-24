"""Strict joined assembly and original instruction comparison."""
import argparse,gzip,hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from reasitic.impedance import assemble
from reasitic.inductance import segment_mutual
from reasitic.polygon import _trig
import audit_mutual_command_traces_original as native


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);a=p.parse_args();root=ROOT/'tests/fixtures'
    f=json.loads(gzip.decompress((root/'join_assembly_original.json.gz').read_bytes()));traces=json.loads(gzip.decompress((root/'join_mutual_traces_original.json.gz').read_bytes()))
    assert hashlib.sha256((root/'join_sessions_original.json.gz').read_bytes()).hexdigest()==f['parent_sha256']
    for name,digest in traces['parents'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
    differences=[];counts={}
    for c in f['cases']:
        assert c['control_before']==c['control_after']==0x37f
        wires=[struct.unpack('<8d',bytes.fromhex(r['wire_bits']))for r in c['records']]
        pairs=[segment_mutual(x,y)for i,x in enumerate(wires)for y in wires[i+1:]]
        matrix=assemble(wires,[(r['sheet_resistance'],r['thickness_count'])for r in c['records']],pairs,c['frequency']);expected=bytes.fromhex(c['upper_bits']);at=0
        for j in range(c['n']):
            for i in range(j+1):
                actual=struct.pack('<2d',matrix[i][j].real,matrix[i][j].imag);counts['upper_entries']=counts.get('upper_entries',0)+1
                if actual!=expected[at:at+16]:differences.append(dict(kind='upper',first=i,second=j,actual=actual.hex(),original=expected[at:at+16].hex()))
                at+=16
    for c in traces['cases']:
        assert c['control_before']==c['control_after']==0x37f
        args=native.doubles(c['input_bits']);actual=native.f64(segment_mutual(args[:8],args[8:]));counts['complete_pairs']=counts.get('complete_pairs',0)+1
        if actual!=c['output_bits']:differences.append(dict(kind='complete_pair',first=c['first'],second=c['second'],actual=actual,original=c['output_bits']))
        for e in c['events']:
            for op in e.get('math',[]):
                value=_trig(native.operand(op['input_words'][0]),False)if op['operation']=='fsin'else native.instruction(op);actual=native.raw(value);counts['instruction_words']=counts.get('instruction_words',0)+1
                if actual!=op['output_words']:
                    original=native.operand(op['output_words']);differences.append(dict(kind=op['operation'],first=c['first'],second=c['second'],address=op['address'],input_words=op['input_words'],actual=actual,original=op['output_words'],actual_binary64=struct.pack('<d',float(value)).hex(),original_binary64=struct.pack('<d',float(original)).hex()))
    report=dict(counts=counts,differences=differences)
    if a.output:a.output.write_text(json.dumps(report,indent=2)+'\n')
    else:
        for row in differences:print(json.dumps(row,separators=(',',':')))
    print(json.dumps(dict(counts=counts,differences=len(differences))))
    raise SystemExit(int(bool(differences)))


if __name__=='__main__':main()
