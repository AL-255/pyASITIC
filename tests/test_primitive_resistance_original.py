"""Original raw standalone-via RESIS/RESISHF input and return stores."""
import hashlib,json,struct,unittest
from pathlib import Path
from reasitic import Technology,build,resistance_dc,resistance_hf
from reasitic.resistance import _records,_retained,_compiled
from array import array


class OriginalPrimitiveResistanceTests(unittest.TestCase):
    def test_every_original_retained_via_return(self):
        root=Path(__file__).parent/'fixtures';f=json.loads((root/'primitive_resistance_original.json').read_text())
        self.assertEqual(hashlib.sha256((root/'primitive_original.json').read_bytes()).hexdigest(),f['parent_sha256']);self.assertEqual(len(f['cases']),4)
        tech=Technology.from_text(f['technology']);returns=0
        for c in f['cases']:
            s=build('via',technology=tech,native_interactive=True,**c['parameters']);rows=_records(s,tech);self.assertEqual(len(rows),1)
            original=c['inputs'][0];row=rows[0]
            self.assertEqual(struct.pack('<7d',*row[:7]),struct.pack('<7d',*original['endpoints'],original['width']))
            self.assertEqual(row[8:], [original['resistance'],1.,original['nx'],original['ny']])
            self.assertEqual(len(c['events']),8)
            for e in c['events']:
                r=_retained(rows,e.get('frequency_hz'));self.assertEqual(struct.pack('<IIH',*r.words()).hex(),e['extended_bits'])
                result=resistance_dc(s,tech)if e['operation']=='dc'else resistance_hf(s,tech,e['frequency_hz'])
                self.assertEqual(struct.pack('<d',result),struct.pack('<d',float(r)))
                if _compiled is not None:
                    data=array('d',(v for row in rows for v in row));out=array('d',[0.])*4
                    self.assertEqual(_compiled(data,out,0 if e['operation']=='dc'else 1,e.get('frequency_hz',0.)),0)
                    self.assertEqual(struct.pack('<IIH',*(int(v)for v in out[1:])).hex(),e['extended_bits'])
                returns+=1
        self.assertEqual(returns,32)
