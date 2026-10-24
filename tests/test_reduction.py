"""Original full-inverse to reduced-matrix spill stores, including double rounding."""
import gzip,json,struct,unittest
from pathlib import Path
from reasitic.reduction import sum_complex


class OriginalReductionTests(unittest.TestCase):
    def test_all_original_reduced_upper_cells(self):
        fixture=json.loads(gzip.decompress((Path(__file__).parent/'fixtures/mesh_inputs_original.json.gz').read_bytes()))
        changed=0
        for index,c in enumerate(fixture['cases']):
            with self.subTest(index=index):
                inverse=c['inversions']['events'][1];n=inverse['n'];data=bytes.fromhex(inverse['output_bits']);matrix=[[0j]*n for _ in range(n)];offset=0
                for j in range(n):
                    for i in range(j+1):matrix[i][j]=matrix[j][i]=complex(*struct.unpack_from('<2d',data,offset));offset+=16
                count=c['lmat']['counts'][0];sizes=[w*t for w,t in zip(count['width'],count['thickness'])];groups=[];offset=0
                for size in sizes:groups.append(range(offset,offset+size));offset+=size
                expected=bytes.fromhex(c['inversions']['events'][2]['input_bits']);offset=0
                for j,columns in enumerate(groups):
                    for rows in groups[:j+1]:
                        values=[matrix[r][col]for r in rows for col in columns]
                        actual=sum_complex(iter(values));word=struct.pack('<2d',actual.real,actual.imag)
                        self.assertEqual(word,expected[offset:offset+16]);offset+=16
                        real=imag=0.
                        for z in values:real+=z.real;imag+=z.imag
                        changed+=struct.pack('<2d',real,imag)!=word
                self.assertEqual(offset,len(expected))
        self.assertGreater(changed,0,'The captured native inputs must detect direct-binary64 summation')

    def test_empty_and_single_input(self):
        self.assertEqual(sum_complex(iter(())),0j)
        value=complex(1e250,-1e-250)
        self.assertEqual(sum_complex(iter((value,))),value)
