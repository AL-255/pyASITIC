"""Exact portable pre-via matrices for the small original systems.

The packaged audit also requires every selected larger system through 384
filaments. This test keeps a small portable-backend regression independently.
"""
import gzip,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from audit_shared_heap_original import ported_impedance,compare


class ImpedancePreparationTests(unittest.TestCase):
    def test_portable_small_original_pre_via_systems(self):
        fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/shared_heap_original.json.gz').read_bytes()))
        cases=fixture['cases'][:12]
        self.assertEqual({c['label'].split('/')[1]for c in cases},{'1','2'})
        for case in cases:
            with self.subTest(label=case['label'],mode=case['cache_mode']):
                prepared=ported_impedance(case)
                self.assertEqual(prepared.filaments,case['matrices']['ind_full']['size'])
                self.assertEqual(len(prepared.reduced_z),case['via']['matrix']['size'])
                result=compare(case,impedance=prepared.reduced_z)
                self.assertEqual(result['differences'],[])
                self.assertEqual(result['ind_input_words_checked'],2*len(prepared.reduced_z)**2)
