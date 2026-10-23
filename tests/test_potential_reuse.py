import json
from pathlib import Path
import unittest
from unittest.mock import patch
from reasitic import Technology,build
import reasitic.potential as potential


class PotentialReuseTests(unittest.TestCase):
    def test_zero_term_reuse_preserves_results_across_frequency_and_process_edits(self):
        case=next(c for c in json.loads((Path(__file__).parent/"fixtures/potential.json").read_text())["cases"]
                  if c["process"]=="CMOS" and c["ground"])
        technology=Technology.from_text(case["technology"])
        technology.chip.update(fftx=64,ffty=64,chipx=128,chipy=128)
        shape=build(case["kind"],technology=technology,**case["parameters"])
        ground=build("wire",technology=technology,**case["ground"])
        original=potential._contact_potential
        def uncached(*args):return original(*args[:-1],zero_terms=None)
        def solve(frequency):
            return potential.solve_capacitance(shape,technology,frequency,ground=ground,
                length_cell=case["length_cell"],width_cell=case["width_cell"],include_potential=True)
        with patch("reasitic.contact_kernel._compiled_contact_pair",None):
            for frequency,rho in ((1e9,10.),(5e9,10.),(1e9,50.)):
                with self.subTest(frequency=frequency,rho=rho):
                    technology.substrate[0]["rho"]=rho
                    reused=solve(frequency)
                    with patch.object(potential,"_contact_potential",uncached):reference=solve(frequency)
                    self.assertEqual(json.dumps(reused,allow_nan=False),json.dumps(reference,allow_nan=False),"Complete result bytes changed")
