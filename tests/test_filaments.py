import copy,json,math,struct,unittest
from pathlib import Path
from reasitic.filament import filament_records


class FilamentTests(unittest.TestCase):
    def test_original_filament_records(self):
        fixture=json.loads((Path(__file__).parent/"fixtures/filaments.json").read_text())
        records=[c["input"] for c in fixture["cases"]];before=copy.deepcopy(records)
        actual=filament_records(records)
        self.assertEqual(before,records,"Filament inputs changed")
        self.assertEqual(len(actual),len(records))
        branches=[0]*4
        for i,(row,c) in enumerate(zip(actual,fixture["cases"])):
            p=c["input"];kind=0
            if p[12]/p[17]>p[18]:
                edges=int(.4*p[23]);kind=1 if p[20]<edges else 3 if p[20]>p[18]-edges-1 else 2
            branches[kind]+=1
            for j,(value,bits) in enumerate(zip(row,c["output_bits"])):
                expected=struct.unpack("<d",bytes.fromhex(bits))[0]
                if math.isnan(expected):self.assertTrue(math.isnan(value),(i,j))
                else:self.assertEqual(struct.pack("<d",value).hex(),bits,(i,j,value,expected))
        self.assertTrue(all(branches),branches)


if __name__=="__main__":unittest.main()
