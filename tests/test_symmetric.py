import json
import math
import struct
import hashlib
from pathlib import Path
import unittest
from reasitic.symmetric import factor_symmetric_upper,inverse_symmetric,_eigen2
from reasitic.green import _guard


class SymmetricTests(unittest.TestCase):
    def compare(self,actual,expected):
        if isinstance(expected,str):
            if expected=="nan":self.assertTrue(math.isnan(actual))
            else:self.assertEqual(actual,float(expected))
        else:self.assertAlmostEqual(actual,expected,delta=max(1e-12,abs(expected)*1e-10))

    def test_native_factors_pivots_and_inverse(self):
        cases=json.loads((Path(__file__).parent/"fixtures/symmetric.json").read_text())["cases"]
        for case in cases:
            a=[[complex(*z) for z in row] for row in case["matrix"]]
            with self.subTest(n=len(a),stride=case["stride"],status=case["S"]):
                if case["S"]:
                    with self.assertRaisesRegex(ValueError,"Singular"):inverse_symmetric(a)
                    continue
                factor,pivots=factor_symmetric_upper(a);self.assertEqual(pivots,case["P"])
                for actual,key in ((factor,"F"),(inverse_symmetric(a),"I")):
                    for i,row in enumerate(actual):
                        for j in range(i,len(a)):
                            for value,reference in zip((row[j].real,row[j].imag),case[key][i][j]):
                                if isinstance(reference,str):self.compare(value,reference)
                                else:self.assertEqual(struct.pack('<d',value),struct.pack('<d',reference))

    def large_matrices(self,n,kind):
        cases=json.loads((Path(__file__).parent/'fixtures/symmetric_large.json').read_text())['cases']
        selected=[c for c in cases if c['n']==n and c['kind']==kind];self.assertTrue(selected)
        def digest(a):return hashlib.sha256(b''.join(struct.pack('<dd',a[i][j].real,a[i][j].imag)for i in range(len(a))for j in range(i,len(a)))).hexdigest()
        for c in selected:
            with self.subTest(n=n,kind=c['kind']):
                a=[]
                for i in range(n):
                    row=[]
                    for j in range(n):
                        if i==j:z=complex(3+i*.01,2)if c['kind']=='dominant'else complex(.001*(i+1),.003)
                        elif c['kind']=='paired'and j==(i^1):z=complex(1,.2)
                        else:z=complex(.01/(i+j+1),.02/(abs(i-j)+1))
                        row.append(z)
                    a.append(row)
                self.assertEqual(digest(a),c['input_sha256'])
                factor,pivots=factor_symmetric_upper(a)
                self.assertEqual(pivots,c['P'])
                self.assertEqual(digest(factor),c['factor_sha256'])
                print(f'Original {n} {kind} factor digest matches; computing complete inverse',flush=True)
                self.assertEqual(digest(inverse_symmetric(a)),c['inverse_sha256'])
                self.assertEqual(digest(a),c['input_sha256'],'Caller matrix changed')

    def test_original_128_dominant_digests(self):self.large_matrices(128,'dominant')
    def test_original_256_dominant_digests(self):self.large_matrices(256,'dominant')
    def test_original_256_paired_digests(self):self.large_matrices(256,'paired')

    def test_native_eigen_rotations(self):
        cases=json.loads((Path(__file__).parent/"fixtures/symmetric.json").read_text())["eigen"]
        for case in cases:
            with self.subTest(values=case["input"]):
                actual=_guard(_eigen2)(*(complex(*z) for z in case["input"]))
                for z,expected in zip(actual,case["result"]):
                    for value,reference in zip((z.real,z.imag),expected):self.compare(value,reference)
