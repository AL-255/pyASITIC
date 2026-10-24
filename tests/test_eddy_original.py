"""Intact original Green returns, callback traces and physical eddy stamps."""
import base64
from fractions import Fraction
import json
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zlib
from reasitic.eddy import add_eddy
from reasitic.green_integration import GreenLayers,GreenIntegrationState,green_integral


class OriginalEddyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).parent/'fixtures'
        cls.reflection=json.loads((root/'eddy_original.json').read_text())
        cls.layered=json.loads((root/'layered_eddy_original.json').read_text())

    def green_calls(self,fixture):
        count=0
        for index,c in enumerate(fixture['cases']):
            first=c['green'][0]
            state=GreenIntegrationState(GreenLayers(*first.get('layers',[1e5,0.,0.])),first.get('kernel','reflection'))
            for j,row in enumerate(c['green']):
                args=struct.unpack('<4d',bytes.fromhex(row['input_bits']));points=[]
                result=green_integral(*args,state,observer=points.append)
                self.assertIs(type(result.value),float,'Public value remains binary64')
                self.assertEqual(struct.pack('<IIH',*result.retained_value.words()).hex(),row['extended_bits'],(index,j,'ST0 return'))
                sig,exponent=struct.unpack('<QH',bytes.fromhex(row['extended_bits']))
                expected=float(Fraction(sig)*Fraction(2)**((exponent&0x7fff)-16383-63)*(-1 if exponent&0x8000 else 1))
                self.assertEqual(struct.pack('<d',result.value),struct.pack('<d',expected))
                self.assertEqual(struct.pack('<'+'d'*len(points),*points),zlib.decompress(base64.b64decode(row['points_zlib_base64'])),(index,j,'Every callback point'))
                self.assertEqual(result.observations,row['observations'])
                self.assertEqual((state.frequency,state.separation,state.height,state.z_offset),args)
                count+=1
        self.assertEqual(count,fixture['coverage']['green'])

    def stamps(self,fixture):
        count=0
        for index,c in enumerate(fixture['cases']):
            for stamp in c['stamps']:
                before=repr(stamp);config=stamp['config'];n=stamp['rows'];metals=int(config[3])
                segments=[]
                for s in stamp['segments']:
                    wire=struct.unpack('<7d',bytes.fromhex(s['wire_bits']))
                    segments.append(SimpleNamespace(start=list(wire[:3]),end=list(wire[3:6]),width=wire[6],primary_width=None,metal=s['metal']))
                shape=SimpleNamespace(kind='square'if stamp['kind']=='square'else'joined',segments=segments,
                                      parameters=dict(length=config[8],width=config[9],spacing=config[10],turns=config[11],metal=0))
                technology=SimpleNamespace(metals=[SimpleNamespace(geometry_height=config[12])for _ in range(metals)],
                                           metal_index=lambda _:0,eddy_layers=[0,1]if config[19]else[0])
                state=GreenIntegrationState(GreenLayers(*config[16:19]),'oscillating'if config[19]else'reflection',history=list(config[13:16]))
                values=struct.unpack('<'+'d'*(2*n*n),bytes.fromhex(stamp['before_bits']))
                matrix=[[complex(*values[2*(j*n+i):2*(j*n+i)+2])for j in range(n)]for i in range(n)]
                # The captured transport already supplies the original layer
                # configuration; no numerical operation is replaced here.
                with patch('reasitic.eddy.configure_eddy',return_value=state):
                    info=add_eddy(matrix,shape,technology,config[6],int(config[4]),[])
                raw=b''.join(struct.pack('<dd',matrix[i][j].real,matrix[i][j].imag)for j in range(n)for i in range(n))
                self.assertEqual(raw.hex(),stamp['after_bits'],(index,'Complete original physical stamp'))
                self.assertEqual(info['green_calls'],stamp['green_count'])
                self.assertEqual(repr(stamp),before,'Captured configuration changed')
                count+=1
        self.assertEqual(count,fixture['coverage']['stamps'])

    def test_original_reflection_green_returns_and_traces(self):self.green_calls(self.reflection)
    def test_original_layered_green_returns_and_traces(self):self.green_calls(self.layered)
    def test_original_reflection_stamps(self):self.stamps(self.reflection)
    def test_original_layered_stamps(self):self.stamps(self.layered)
