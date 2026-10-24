"""Original exponent binary64 outputs and extended range classifications."""
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import struct
import unittest
from reasitic.retained_scalar import Real
from reasitic.x87_math import exp_retained


class OriginalExponentTests(unittest.TestCase):
    def test_original_outputs_and_extended_range(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/exp_original.json').read_text());cases=fixture['cases']
        payload=struct.pack('<I',len(cases));self.assertEqual(len(cases),418)
        for i,c in enumerate(cases):
            low,high,se=c['input_words'];sig=low|(high<<32);e=se&0x7fff;sign=-1 if se&0x8000 else 1
            if e==0x7fff:value=Real(math.copysign(math.inf,sign)if sig==1<<63 else math.nan)
            elif not sig:value=Real(math.copysign(0.,sign))
            else:value=Real(Fraction(sign*sig)*Fraction(2)**((e or 1)-16383-63))
            payload+=struct.pack('<I8d',14,*(-value).words(),0,0,0,0,0)
            actual=exp_retained(value);target=struct.unpack('<d',bytes.fromhex(c['output_bits']))[0]
            if math.isnan(target):self.assertTrue(math.isnan(float(actual)),i)
            else:self.assertEqual(struct.pack('<d',float(actual)).hex(),c['output_bits'],i)
            target_sig,target_se=struct.unpack('<QH',bytes.fromhex(c['extended_bits']))
            if target_se&0x7fff==0x7fff:self.assertEqual(actual.kind,1 if target_sig==1<<63 else 2,i)
            else:
                self.assertEqual(actual.kind,0,i)
                self.assertEqual(actual.words()[2],target_se,i)
                if not target_sig:self.assertEqual(actual.words()[:2],(0,0),i)
        self.assertEqual(hashlib.sha256(payload).hexdigest(),fixture['input_sha256'])
