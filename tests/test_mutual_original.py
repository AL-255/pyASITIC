import json
import math
from pathlib import Path
import struct
import unittest
from reasitic.inductance import segment_mutual
from reasitic.parallel import (segment_self_inductance,cross_section_log_integral,
                               effective_separation,parallel_segment_mutual)


class OriginalMutualTests(unittest.TestCase):
    def test_intact_original_primitive_stores(self):
        self.check_original('mutual_original')

    def test_intact_original_boundary_stores(self):
        self.check_original('mutual_boundaries_original')

    def check_original(self,fixture):
        cases=json.loads((Path(__file__).parent/f'fixtures/{fixture}.json').read_text())['cases']
        for index,c in enumerate(cases):
            mode=c['mode']
            if mode>=5:continue  # Separately identified instruction oracles.
            with self.subTest(index=index,mode=mode):
                args=list(map(float,c['input']));saved=struct.pack('<'+'d'*len(args),*args)
                warnings=[];status=0;first,second=args[:8],args[8:16]
                if mode<3:value=float((segment_self_inductance,cross_section_log_integral,effective_separation)[mode](*args))
                elif mode==3:
                    status,value=parallel_segment_mutual(first,second,args[16])
                    if status:
                        self.assertIsNone(value)
                        value=423.  # The original leaves the caller's cell untouched.
                else:value=segment_mutual(first,second,warnings)
                self.assertEqual(status,c['status'])
                expected=struct.unpack('<d',bytes.fromhex(c['output_bits']))[0]
                if math.isnan(expected):self.assertTrue(math.isnan(value))
                else:self.assertEqual(struct.pack('<d',value).hex(),c['output_bits'])
                if mode==4:self.assertEqual(bool(warnings),bool(c['warnings']))
                self.assertEqual(struct.pack('<'+'d'*len(args),*args),saved)
                if mode>=3:self.assertEqual(struct.pack('<16d',*first,*second),saved[:128])
