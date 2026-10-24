"""Unchanged original transfer calls and complete generated FFT tables."""
import hashlib
import json
import math
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
from reasitic import potential
from reasitic.table_kernel import configuration


def packed(values):
    return b''.join(struct.pack('<dd',z.real,z.imag)for z in values)


class OriginalSpectralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads((Path(__file__).parent/'fixtures/spectral.json').read_text())
        assert len(cls.fixture['tables'])==33
        assert sum(len(c['requests'])for c in cls.fixture['scalar'])==1728

    def inputs(self,c):
        coefficients=tuple(complex(*map(float,z))for z in c['coefficients'])
        depths=tuple(map(float,c['depths']))
        records=tuple(tuple(row)for row in c['metals'])
        args=(c['source'],c['target'],c['nx'],c['ny'],c['width'],c['height'],records,coefficients,depths)
        self.assertEqual(hashlib.sha256(configuration(*args).tobytes()).hexdigest(),c['input_sha256'])
        return args

    def components_equal(self,actual,expected,label):
        self.assertEqual(len(actual),len(expected),label)
        for i,(value,want)in enumerate(zip(actual,expected)):
            if want=='nan':self.assertTrue(math.isnan(value),(label,i))
            elif isinstance(want,str):self.assertEqual(value,float(want),(label,i))
            else:self.assertEqual(struct.pack('<d',value),struct.pack('<d',want),(label,i))

    def test_original_transfer_and_regional_calls(self):
        for index,c in enumerate(self.fixture['scalar']):
            before=repr(c);*_,coefficients,original_depths=self.inputs(c)
            depths=list(original_depths);saved=struct.pack('<'+'d'*len(depths),*depths)
            actual=[]
            for request in c['requests']:
                kind,source,target,last,k,sh,th=request;k,sh,th=map(float,(k,sh,th))
                if kind in (0,1):
                    u,v=potential._transfer(kind==1,source if kind==1 else 0,last if kind==1 else source,k,coefficients,depths)
                    value=potential._divide(u,v)
                elif kind in (2,3):value=potential._source(kind==3,source,last,k,sh,coefficients,depths)
                else:value=potential._spectral(kind==4,source,target,last,k,sh,th,coefficients,depths)
                actual.extend((value.real,value.imag))
                self.assertEqual(struct.pack('<'+'d'*len(depths),*depths),saved,(index,request,'Depths changed'))
            self.components_equal(actual,c['output'],index)
            self.assertEqual(repr(c),before)

    def tables(self,predicate):
        selected=[(i,c)for i,c in enumerate(self.fixture['tables'])if predicate(c)]
        self.assertTrue(selected)
        for index,c in selected:
            with self.subTest(index=index):
                before=repr(c);args=self.inputs(c)
                result=potential._tables(*args)
                nx,ny=c['nx'],c['ny']
                self.assertEqual(tuple(map(len,result)),(2*nx,2*ny,max((nx+1)*(ny+1),nx*(nx+1)+ny+1)))
                values=[z for table in result for z in table]
                if 'output_sha256'in c:self.assertEqual(hashlib.sha256(packed(values)).hexdigest(),c['output_sha256'])
                else:self.components_equal([v for z in values for v in(z.real,z.imag)],c['output'],index)
                self.assertEqual(repr(c),before)
                self.inputs(c)

    def test_original_small_and_nonfinite_tables(self):
        self.tables(lambda c:max(c['nx'],c['ny'])<=16 or c['nx']!=c['ny'])

    def test_original_32_tables(self):
        self.tables(lambda c:c['nx']==c['ny']==32)

    def test_original_64_tables(self):
        self.tables(lambda c:c['nx']==c['ny']==64)

    def test_original_128_tables(self):
        self.tables(lambda c:c['nx']==c['ny']==128)

    def test_original_256_source_0_target_0(self):
        self.tables(lambda c:c['nx']==c['ny']==256 and(c['source'],c['target'])==(0,0))

    def test_original_256_source_0_target_1(self):
        self.tables(lambda c:c['nx']==c['ny']==256 and(c['source'],c['target'])==(0,1))

    def test_original_256_source_1_target_0(self):
        self.tables(lambda c:c['nx']==c['ny']==256 and(c['source'],c['target'])==(1,0))

    def test_table_cache_preserves_input_zero_signs(self):
        args=list(self.inputs(self.fixture['tables'][0]))
        potential._cached_tables.cache_clear()
        try:
            with patch.object(potential,'generate_tables',return_value=None),patch.object(potential,'_retained_tables',return_value=([],[],[]))as generate:
                args[-2]=(complex(1.,0.),*args[-2][1:])
                potential._tables(*args);potential._tables(*args)
                self.assertEqual(generate.call_count,1)
                args[-2]=(complex(1.,-0.),*args[-2][1:])
                potential._tables(*args);potential._tables(*args)
                self.assertEqual(generate.call_count,2)
                self.assertEqual(struct.pack('<d',generate.call_args.args[-2][0].imag),struct.pack('<d',-0.))
        finally:potential._cached_tables.cache_clear()
