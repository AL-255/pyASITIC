import unittest
from reasitic import Technology,build_device,coupling_estimate
from reasitic.bridge import handle


class DeviceTests(unittest.TestCase):
    def test_paired_preview_and_winding_analysis(self):
        for kind in ("transformer","balun"):
            definition=dict(kind=kind,parameters=dict(name="T",turns=3 if kind=="balun" else 1.5,width=3,secondary_width=4,metal="M4",exit_metal="M3"))
            first=handle(dict(action="build",**definition,winding=0))
            second=handle(dict(action="build",**definition,winding=1))
            self.assertEqual(first["windings"],["T-P","T-S"])
            self.assertNotEqual(first["name"],second["name"])
            self.assertEqual(len(first["polygons"]),len(second["polygons"]))
            for p,q in zip(first["polygons"],second["polygons"]):
                for a,b in zip(p["points"],q["points"]):
                    for axis in range(2):
                        self.assertAlmostEqual(a[axis]+first["origin"][axis],b[axis]+second["origin"][axis])
            for winding in (0,1):
                estimate=handle(dict(action="simulate",**definition,winding=winding,frequency_hz=1e9))
                self.assertGreater(estimate["inductance_nh"],0)
            coupling=handle(dict(action="coupling",first=dict(**definition,winding=0),second=dict(**definition,winding=1)))
            self.assertGreater(abs(coupling["k"]),0)
