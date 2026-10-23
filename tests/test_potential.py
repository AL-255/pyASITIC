import json
import os
from pathlib import Path
import unittest
from reasitic import Technology,build
from reasitic.potential import solve_capacitance,_tables
from reasitic.table_kernel import layer_coefficients


def cases_for_run():
    cases=json.loads((Path(__file__).parent/"fixtures/potential.json").read_text())["cases"]
    process=os.environ.get("REASITIC_POTENTIAL_PROCESS")
    frequency=os.environ.get("REASITIC_POTENTIAL_FREQUENCY")
    if process is not None:cases=[c for c in cases if c["process"]==process]
    if frequency is not None:cases=[c for c in cases if c["frequency_hz"]==float(frequency)]
    if not cases:raise ValueError("No native potential fixtures match the selected process/frequency")
    return sorted(cases,key=lambda item:(item["process"],item["frequency_hz"]))


def progress(message):
    if os.environ.get("CI"):print(message,flush=True)


class PotentialTests(unittest.TestCase):
    def test_mesh_resolution_and_coordinate_errors(self):
        technology=Technology.default()
        with self.assertRaisesRegex(ValueError,"outside"):
            solve_capacitance(build("wire",length=40,width=5,x=-1,technology=technology),technology,1e9)
        with self.assertRaisesRegex(ValueError,"collapses"):
            solve_capacitance(build("wire",length=40,width=.01,x=10,y=20,technology=technology),technology,1e9)
        with self.assertRaisesRegex(ValueError,"contact limit"):
            solve_capacitance(build("square",length=100,width=5,turns=2,technology=technology),technology,1e9,
                              length_cell=1e-100,width_cell=1e-100,max_contacts=2)

    def test_connected_native_admittance_matrices(self):
        for case in cases_for_run():
            progress(f"CAP: {case['process']} {case['frequency_hz']/1e9:g} GHz · {case['kind']} · ground={bool(case['ground'])}")
            with self.subTest(kind=case["kind"],process=case["process"],frequency=case["frequency_hz"],ground=bool(case["ground"])):
                technology=Technology.from_text(case["technology"])
                shape=build(case["kind"],technology=technology,**case["parameters"])
                ground=build("wire",technology=technology,**case["ground"]) if case["ground"] else None
                result=solve_capacitance(shape,technology,case["frequency_hz"],ground=ground,length_cell=case["length_cell"],width_cell=case["width_cell"],include_potential=True)
                self.assertEqual(len(result["matrix"]),len(case["matrix"]))
                for i,(row,expected) in enumerate(zip(result["matrix"],case["matrix"])):
                    for j,(value,reference) in enumerate(zip(row,expected)):
                        for axis in range(2):
                            self.assertAlmostEqual(value[axis],reference[axis],delta=max(1e-16,abs(reference[axis])*1e-8),msg=f"YC {i},{j} component {axis}")
                self.assertEqual(len(result["potential_matrix"]),len(case["potential"]))
                for i,(row,expected) in enumerate(zip(result["potential_matrix"],case["potential"])):
                    for j,(value,reference) in enumerate(zip(row,expected)):
                        for axis in range(2):
                            self.assertAlmostEqual(value[axis],reference[axis],delta=max(1e-9,abs(reference[axis])*1e-8),msg=f"Pmat {i},{j} component {axis}")

    def test_actual_native_fft_cache_samples(self):
        for case in cases_for_run():
            technology=Technology.from_text(case["technology"])
            depths=[0.]*(len(technology.substrate)+1)
            for i in range(len(technology.substrate)-1,-1,-1):
                depths[i]=depths[i+1]+technology.substrate[i]["t"]
            coefficients=layer_coefficients(technology.substrate,case["frequency_hz"])
            records=tuple((metal.layer,depths[metal.layer]-metal.height,metal.thickness) for metal in technology.metals)
            nx,ny=int(technology.chip["fftx"]),int(technology.chip["ffty"])
            for pair in case["greens"]:
                progress(f"FFT reference: {case['process']} {case['frequency_hz']/1e9:g} GHz · metal pair {pair['source']},{pair['target']} · {nx}×{ny}")
                with self.subTest(process=case["process"],frequency=case["frequency_hz"],pair=(pair["source"],pair["target"])):
                    tx,ty,txy=_tables(pair["source"],pair["target"],nx,ny,technology.chip["chipx"],technology.chip["chipy"],records,coefficients,tuple(depths))
                    samples=[(tx[index],reference) for index,reference in pair["x"]]+[(ty[index],reference) for index,reference in pair["y"]]
                    samples.extend((txy[x*(nx+1)+y],reference) for x,y,reference in pair["xy"])
                    for value,reference in samples:
                        for actual,expected in zip((value.real,value.imag),reference):
                            self.assertAlmostEqual(actual,expected,delta=max(1e-9,abs(expected)*1e-9))
