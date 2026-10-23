import base64
import json
import unittest
from reasitic.bridge import handle,request_json


class BridgeTests(unittest.TestCase):
    def test_generation_simulation_sweep_and_download(self):
        definition=dict(kind="square",parameters=dict(name="TEST",width=3,length=80,height=70,turns=1.25,metal="M4",exit_metal="M3"))
        shape=handle(dict(action="build",**definition))
        self.assertEqual(len(shape["segments"]),7)
        simulation=handle(dict(action="simulate",frequency_hz=1e9,**definition))
        self.assertGreater(simulation["hf_ohm"],simulation["dc_ohm"])
        self.assertGreater(simulation["inductance_nh"],0)
        sweep=handle(dict(action="sweep",first_hz=1e8,last_hz=1e10,count=21,**definition))
        self.assertEqual(len(sweep["rows"]),21)
        self.assertEqual(sweep["rows"][0]["frequency_hz"],1e8)
        self.assertAlmostEqual(sweep["rows"][-1]["hf_ohm"],handle(dict(action="simulate",frequency_hz=1e10,**definition))["hf_ohm"])
        stream=base64.b64decode(handle(dict(action="gds",**definition))["base64"])
        self.assertEqual(stream[:4],bytes.fromhex("00060002"))
        self.assertEqual(stream[-4:],bytes.fromhex("00040400"))
        matrix=handle(dict(action="lmat",frequency_hz=2e9,mesh=dict(length_cell=50,width_cell=3,thickness_cell=.5),**definition))
        self.assertFalse(matrix["eddy"])
        self.assertEqual(len(matrix["matrix"]),matrix["segments"])
        self.assertGreater(matrix["inductance_h"],0)

    def test_invalid_requests_return_errors(self):
        for payload in ["{",'{"action":"unknown"}','{"parameters":{"turns":-2}}','{"parameters":{"length":NaN}}']:
            self.assertIn("error",json.loads(request_json(payload)))

    def test_invalid_sweep(self):
        with self.assertRaises(ValueError):
            handle(dict(action="sweep",first_hz=1e9,last_hz=1e8))
