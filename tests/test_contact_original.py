"""Intact original matrices, including complete 256-contact output digests."""
import hashlib
import json
import math
from pathlib import Path
import struct
import unittest
from reasitic.potential import Contact,_contact_potential


def packed(values):
    return b''.join(struct.pack('<dd',z.real,z.imag)for z in values)


class OriginalContactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture=json.loads((Path(__file__).parent/'fixtures/contact_potential.json').read_text())
        cls.cases=fixture['cases']
        assert sum(2*len(c['contacts'])**2 for c in cls.cases)==fixture['components']

    def check_case(self,index,c):
        before=repr(c);nx,ny=c['nx'],c['ny'];cells=max((nx+1)*(ny+1),nx*(nx+1)+ny+1)
        tables={};pairs={(p['low'],p['high']):p for p in c['pairs']}
        def get_table(low,high):
            key=low,high
            if key not in tables:
                p=pairs[key];seed=p['seed']
                def scaled(value,scale):
                    return math.copysign(math.inf,value if value else 1)if scale=='inf'else value*scale
                values=[complex(scaled((i*8191+seed*17)%65521-32760,c['scale'][0]),
                                scaled((i*257+seed*31)%4093-2046,c['scale'][1]))for i in range(2*nx+2*ny+cells)]
                self.assertEqual(hashlib.sha256(packed(values)).hexdigest(),p['input_sha256'])
                tables[key]=values[:2*nx],values[2*nx:2*nx+2*ny],values[2*nx+2*ny:]
            return tables[key]
        contacts=[Contact(*row)for row in c['contacts']];coefficients=[complex(*z)for z in c['coefficients']]
        zero_terms={};matrix=[]
        for a in contacts:
            row=[]
            for b in contacts:
                table=get_table(min(a.metal,b.metal),max(a.metal,b.metal))
                row.append(_contact_potential(a,b,nx,ny,c['width'],c['height'],c['metals'],coefficients,c['depths'],table,zero_terms))
            matrix.append(row)
        if c.get('digest_only'):
            self.assertEqual(hashlib.sha256(packed(z for row in matrix for z in row)).hexdigest(),c['output_sha256'],f'Complete original matrix {index}')
        else:
            for i,row in enumerate(matrix):
                for j,z in enumerate(row):
                    for k,value in enumerate((z.real,z.imag)):
                        expected=c['output'][i][j][k]
                        if expected=='nan':self.assertTrue(math.isnan(value),(index,i,j,k))
                        elif isinstance(expected,str):self.assertEqual(value,float(expected))
                        else:self.assertEqual(struct.pack('<d',value),struct.pack('<d',expected),(index,i,j,k))
        self.assertEqual(repr(c),before,'Contact metadata changed')
        for key,values in tables.items():
            self.assertEqual(hashlib.sha256(packed(z for table in values for z in table)).hexdigest(),pairs[key]['input_sha256'],'Input table changed')

    def test_original_small_matrices(self):
        for i,c in enumerate(self.cases):
            if not c.get('digest_only'):
                with self.subTest(index=i):self.check_case(i,c)

    def test_original_full_single_metal_matrix(self):
        for i,c in enumerate(self.cases):
            if c.get('digest_only')and len(c['pairs'])==1:
                with self.subTest(index=i):self.check_case(i,c)

    def test_original_full_multi_metal_matrix(self):
        for i,c in enumerate(self.cases):
            if c.get('digest_only')and len(c['pairs'])>1:
                with self.subTest(index=i):self.check_case(i,c)
