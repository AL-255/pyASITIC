import json
import math
from pathlib import Path
import unittest
from reasitic.linear import factor_general,inverse_general,solve_general,matrix_vector
from reasitic.solver import _sum_complex

FIXTURE=Path(__file__).parent/"fixtures/general.json"


def right_sides(n):
    return [[complex(i==r,0) for i in range(n)] for r in (0,n-1)]+[[complex((i%7-3)*.125,(i%11-5)*.0625) for i in range(n)]]


class GeneralLinearTests(unittest.TestCase):
    def test_native_sum_order_at_cancellation(self):
        # Python 3.14's complex sum compensates away the original binary64
        # accumulation spill. CAP reduction and node stamping need the latter.
        self.assertEqual(_sum_complex([1e16+1e16j,1+1j,-1e16-1e16j]),0j)

    def assert_components(self,actual,expected):
        self.assertEqual(len(actual),len(expected))
        for row,reference in zip(actual,expected):
            self.assertEqual(len(row),len(reference))
            for value,pair in zip(row,reference):
                for part,target in zip((value.real,value.imag),pair):
                    if target=="nan":self.assertTrue(math.isnan(part))
                    elif target in ("inf","-inf"):self.assertEqual(part,float(target))
                    else:self.assertAlmostEqual(part,target,delta=max(1e-13,abs(target)*1e-12))

    def test_original_general_factors_inverses_solves_and_products(self):
        for c in json.loads(FIXTURE.read_text())["cases"]:
            if "matrix" not in c or any(isinstance(v,str) for row in c["matrix"] for z in row for v in z):continue
            with self.subTest(n=len(c["matrix"]),status=c["S"]):
                a=[[complex(*z) for z in row] for row in c["matrix"]]
                saved=[row.copy() for row in a];rhs=right_sides(len(a))
                self.assert_components([matrix_vector(a,b) for b in rhs],c["V"])
                if c["S"]:
                    for function in (factor_general,inverse_general):
                        with self.assertRaisesRegex(ValueError,"Singular"):function(a)
                    continue
                factor,pivots=factor_general(a)
                self.assertEqual(pivots,c["P"],"Original IZAMAX pivots")
                self.assert_components(factor,c["F"])
                self.assert_components(inverse_general(a),c["I"])
                self.assert_components([solve_general(factor,pivots,b) for b in rhs],c["B"])
                self.assertEqual(a,saved,"Caller input changed")

    def test_panel_boundary_and_inverse_workspace_sequence(self):
        c=next(c for c in json.loads(FIXTURE.read_text())["cases"] if c.get("n")==65)
        n=c["n"]
        a=[[complex(3+i*.01,2) if j==(i+13)%n else complex(.01/(i+j+1),.02/(abs(i-j)+1)) for j in range(n)] for i in range(n)]
        factor,pivots=factor_general(a)
        self.assertEqual(pivots,c["P"],"Original pivots across the 64-column panel")
        inverse=inverse_general(a)
        for i in range(n):
            for j in range(n):
                value=sum(a[i][k]*inverse[k][j] for k in range(n))
                self.assertLessEqual(abs(value-(i==j)),1e-11)
        for rhs in right_sides(n):
            result=solve_general(factor,pivots,rhs)
            for value,target in zip(matrix_vector(a,result),rhs):self.assertLessEqual(abs(value-target),1e-11)

    def test_tiny_nonzero_pivots_are_retained(self):
        a=[[1e-100+0j,0j],[0j,2e-100+0j]]
        factor,pivots=factor_general(a)
        self.assertEqual(pivots,[0,1])
        self.assertEqual(solve_general(factor,pivots,[1e-100+0j,2e-100+0j]),[1+0j,1+0j])
        inverse=inverse_general(a)
        self.assertEqual(inverse[0][0],1e100+0j)
        self.assertEqual(inverse[1][1],5e99+0j)

    def test_invalid_dimensions_and_pivots(self):
        for a in ([],[[1j,0j]]):
            for function in (factor_general,inverse_general):
                with self.assertRaisesRegex(ValueError,"nonempty square"):function(a)
        with self.assertRaisesRegex(ValueError,"match"):solve_general([[1+0j]],[0],[])
        with self.assertRaisesRegex(ValueError,"pivot"):solve_general([[1+0j]],[1],[1+0j])
        with self.assertRaisesRegex(ValueError,"match"):matrix_vector([[1+0j]],[])
