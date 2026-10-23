import json
import math
from pathlib import Path
import struct
import unittest
from decimal import Decimal,localcontext
from fractions import Fraction
from reasitic.potential import _fft,_transform_grid,_fft_extended,_fft_spill
from reasitic.inductance import _round_extended


class PotentialFftTests(unittest.TestCase):
    def test_original_potential_fft_and_reflected_grids(self):
        cases=json.loads((Path(__file__).parent/"fixtures/potential_fft.json").read_text())["cases"]
        for c in cases:
            with self.subTest(grid=c["grid"],nx=c["nx"],ny=c["ny"],scale=c["scale"]):
                values=[complex(*z) for z in c["input"]]
                if c["grid"]:_transform_grid(values,c["nx"],c["ny"])
                else:_fft(values)
                for value,expected in zip(values,c["output"]):
                    for actual,target in zip((value.real,value.imag),expected):
                        self.assertEqual(struct.pack('d',actual),struct.pack('d',target),"Native FFT bits, including signed zero")

    def test_exact_quantum_scaling_and_signed_zero(self):
        with localcontext() as context:
            context.prec=2048
            for exponent in (-1200,-1100,-1074,-1022,-700,-257,-256,-128,-65,-64,-53,-1,0,1,64,128,256,257,700,1023):
                for base in (Decimal(0),Decimal('-0'),Decimal(1),Decimal('-1'),Decimal('1.234567890123456789012345'),Decimal('0.500000000000000000000001')):
                    value=base*Decimal(2)**exponent
                    actual=_fft_extended(value)
                    expected=_round_extended(Fraction(value))
                    self.assertEqual(Fraction(actual),expected)
                    if not value:self.assertEqual(actual.is_signed(),value.is_signed())
                    self.assertEqual(struct.pack('d',_fft_spill(value)),struct.pack('d',float(expected) if value else float(value)))
