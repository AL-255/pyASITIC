import json
import math
from pathlib import Path
import unittest
from reasitic.parallel import segment_self_inductance,cross_section_log_integral,effective_separation,parallel_segment_mutual
from reasitic.inductance import segment_mutual


class ParallelTests(unittest.TestCase):
    def test_native_retained_parallel_kernels(self):
        cases=json.loads((Path(__file__).parent/"fixtures/parallel.json").read_text())["cases"]
        for case in cases:
            mode,args=case["mode"],case["input"]
            with self.subTest(mode=mode,args=args):
                if mode<3:value=float((segment_self_inductance,cross_section_log_integral,effective_separation)[mode](*args))
                elif mode==3:
                    status,value=parallel_segment_mutual(args[:8],args[8:16],args[16]);self.assertEqual(status,case["status"])
                    if status:
                        self.assertIsNone(value);continue
                else:value=segment_mutual(args[:8],args[8:16])
                expected=case["value"]
                if expected=="nan":self.assertTrue(math.isnan(value))
                elif isinstance(expected,str):self.assertEqual(value,float(expected))
                elif expected==0:self.assertEqual(value,0)
                else:self.assertAlmostEqual(value,expected,delta=max(1e-300,abs(expected)*1e-12))
