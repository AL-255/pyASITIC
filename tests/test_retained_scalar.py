from fractions import Fraction
import unittest
from reasitic.retained_scalar import Real


class RetainedScalarTests(unittest.TestCase):
    def test_extended_overflow_and_underflow_ties(self):
        unit=Fraction(2)**(16383-63)
        maximum=((1<<64)-1)*unit
        self.assertEqual(Real._result(maximum+unit/4).words(),(0xffffffff,0xffffffff,0x7ffe))
        self.assertEqual(Real._result(maximum+unit/2).words(),(0,0x80000000,0x7fff))
        self.assertEqual(Real._result(-maximum-unit/2).words(),(0,0x80000000,0xffff))
        self.assertEqual(Real._result(maximum-unit/2).words(),(0xfffffffe,0xffffffff,0x7ffe))
        tiny=Fraction(2)**-16445
        self.assertEqual(Real._result(tiny/2).words(),(0,0,0))
        self.assertEqual(Real._result(-tiny/2).words(),(0,0,0x8000))
        self.assertEqual(Real._result(3*tiny/2).words(),(2,0,0))
        normal=Fraction(2)**-16382
        self.assertEqual(Real._result(normal-tiny).words(),(0xffffffff,0x7fffffff,0))
        self.assertEqual(Real._result(normal-tiny/2).words(),(0,0x80000000,1))
