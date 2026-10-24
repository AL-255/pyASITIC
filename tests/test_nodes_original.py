"""Complete original folded-node boundaries, including asymmetric matrices."""
import base64
import hashlib
import json
import math
from pathlib import Path
import struct
import unittest
import zlib
from reasitic.network import solve_node_equations


class OriginalNodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=json.loads((Path(__file__).parent/'fixtures/nodes_original.json').read_text())['cases']
        assert len(cls.cases)==54

    def cases_at(self,predicate):
        selected=[c for c in self.cases if predicate(c['n'])]
        self.assertTrue(selected)
        for c in selected:
            with self.subTest(label=c['label']):
                n=c['n'];raw=zlib.decompress(base64.b64decode(c['input_zlib_base64']))
                self.assertEqual(len(raw),32*n*n)
                self.assertEqual(hashlib.sha256(raw).hexdigest(),c['input_sha256'])
                values=struct.unpack('<'+'d'*(4*n*n),raw)
                cap,ind=[[[complex(*values[offset+2*(j*n+i):offset+2*(j*n+i)+2])for j in range(n)]for i in range(n)]for offset in(0,2*n*n)]
                y,folded=solve_node_equations(cap,ind)
                def packed(matrices):return b''.join(struct.pack('<dd',m[i][j].real,m[i][j].imag)for m in matrices for j in range(n)for i in range(n))
                self.assertEqual(packed((cap,ind)),raw,'Caller inputs changed')
                self.assertEqual(hashlib.sha256(packed((folded,))).hexdigest(),c['cap_sha256'])
                for value,bits in zip((v for key in('y11','y12','y21','y22')for v in(y[key].real,y[key].imag)),c['Y']):
                    target=struct.unpack('<d',bytes.fromhex(bits))[0]
                    if math.isnan(target):self.assertTrue(math.isnan(value))
                    else:self.assertEqual(struct.pack('<d',value).hex(),bits)

    def test_original_small_nodes(self):self.cases_at(lambda n:n<65)
    def test_original_65_nodes(self):self.cases_at(lambda n:n==65)
    def test_original_128_nodes(self):self.cases_at(lambda n:n==128)
    def test_original_256_nodes(self):self.cases_at(lambda n:n==256)
