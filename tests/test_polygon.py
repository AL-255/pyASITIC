import json
from pathlib import Path
import struct
import unittest
from reasitic.polygon import vertices


class PolygonTests(unittest.TestCase):
    def test_complete_original_polygon_vertex_stores(self):
        cases=json.loads((Path(__file__).parent/'fixtures/polygon_original.json').read_text())['cases']
        for c in cases:
            with self.subTest(label=c['label']):
                rows=vertices(*c['config'])
                self.assertEqual(len(rows),len(c['rows']))
                for i,(row,expected)in enumerate(zip(rows,c['rows'])):
                    self.assertEqual(struct.pack('<12d',*row).hex(),expected,i)
