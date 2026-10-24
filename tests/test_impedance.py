import json
from pathlib import Path
import struct
import unittest
from reasitic.impedance import assemble
from reasitic import Technology,build
from reasitic.solver import discretize
from reasitic.inductance import segment_mutual


class ImpedanceTests(unittest.TestCase):
    def test_original_longitudinal_clone_records(self):
        directory=Path(__file__).parent/'fixtures'
        cases=json.loads((directory/'impedance_original.json').read_text())['cases']
        for c in cases:
            if c['fixture'] not in ('network','network_eddy'):continue
            source=json.loads((directory/f"{c['fixture']}.json").read_text())['cases'][c['index']]
            tech=Technology.from_text(source['technology']);shape=build(source['kind'],technology=tech,**source['parameters'])
            mesh=c['mesh'];clone=discretize(shape,mesh['capacitance_length_cell'],mesh['length_cell'])
            # Changing a clone must never modify another solve or its source,
            # including geometry served from the subdivision cache.
            before=repr(shape)
            pristine=repr(clone)
            clone.segments[0].start[0]+=10.
            clone=discretize(shape,mesh['capacitance_length_cell'],mesh['length_cell'])
            self.assertEqual(repr(clone),pristine)
            self.assertEqual(repr(shape),before)
            actual=[s for s in clone.segments if s.metal<len(tech.metals)]
            seen=set();records=[]
            for r in c['records']:
                raw=r['input']['segment']
                if raw not in seen:seen.add(raw);records.append(bytes.fromhex(raw))
            self.assertEqual(len(actual),len(records))
            for segment,raw in zip(actual,records):
                for field,offset in [('start',0),('end',24),('outer_start',0x44),('outer_end',0x5c),('inner_start',0x88),('inner_end',0xa0)]:
                    self.assertEqual(struct.pack('<3d',*getattr(segment,field)),raw[offset:offset+24],(c['fixture'],c['index'],field))
                self.assertEqual(struct.pack('<dd',segment.width,segment.thickness),raw[0xcc:0xdc])

    def test_complete_original_upper_assembly(self):
        cases=json.loads((Path(__file__).parent/'fixtures/impedance_original.json').read_text())['cases']
        for c in cases:
            with self.subTest(fixture=c['fixture'],index=c['index']):
                wires=[struct.unpack('<8d',bytes.fromhex(r['wire_bits']))for r in c['records']]
                metadata=[(r['sheet_resistance'],r['thickness_count'])for r in c['records']]
                pairs=[segment_mutual(a,b)for i,a in enumerate(wires)for b in wires[i+1:]]
                self.assertEqual([struct.pack('<d',v).hex()for v in pairs],c['mutual_bits'],'Actual original mesh pairs')
                saved=repr((wires,metadata,pairs));matrix=assemble(wires,metadata,pairs,c['frequency']);n=c['n']
                actual=b''.join(struct.pack('<dd',matrix[i][j].real,matrix[i][j].imag)for j in range(n)for i in range(j+1))
                self.assertEqual(actual.hex(),c['upper_bits'])
                self.assertEqual(saved,repr((wires,metadata,pairs)))
                for i in range(n):
                    for j in range(n):self.assertEqual(matrix[i][j],matrix[j][i])
