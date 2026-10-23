import json
from pathlib import Path
import struct
import unittest
from reasitic.x87_math import cosh_argument,tanh_argument


class PotentialMathTests(unittest.TestCase):
    def test_original_clipped_cosh_and_retained_tanh_arguments(self):
        fixture=json.loads((Path(__file__).parent/"fixtures/potential_math.json").read_text())
        for value,expected in fixture["cosh"]:
            self.assertEqual(struct.pack("d",cosh_argument(1.,value,0.)),struct.pack("d",float(expected)),f"Original cosh {value}")
        for values,expected in fixture["tanh"]:
            self.assertEqual(struct.pack("d",tanh_argument(*values)),struct.pack("d",float(expected)),f"Original tanh {values}")
