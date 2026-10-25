"""Lossless native snapshot references preserve all byte and owner targets."""
import base64,copy,gzip,hashlib,json,sys,tempfile,unittest,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from getline_fixture import record_id
from printf_fixture import data,expand_state,unpack_state,pack_state,compact_pages,memory_for
from reasitic.memory import MemoryFault,UnknownMemory
from printf_archive import read_fixture,split_archive


class PrintfFixtureTests(unittest.TestCase):
    def test_split_archive_streams_across_headers_without_changing_any_byte(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);source=root/'dense.json.gz';target=root/'fixture.manifest.json';fixture=dict(cases=[{'label':'sample'}],parents={'parent':'sha'},registers=[1,2,3]);raw=gzip.compress(json.dumps(fixture).encode(),mtime=0);source.write_bytes(raw)
            manifest=split_archive(source,target,histories=1,parents=fixture['parents'],part_bytes=7);self.assertGreater(len(manifest['parts']),2)
            self.assertEqual(b''.join((root/p['file']).read_bytes()for p in manifest['parts']),raw);self.assertEqual(read_fixture(target),fixture);self.assertEqual(read_fixture(source),fixture)

    def test_split_archive_rejects_corruption_missing_parts_and_metadata(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);source=root/'dense.json.gz';target=root/'fixture.manifest.json';fixture=dict(cases=[{}],parents={});source.write_bytes(gzip.compress(json.dumps(fixture).encode(),mtime=0));manifest=split_archive(source,target,histories=1,parents={},part_bytes=7)
            for field,value in (('sha256','bad'),('histories',2),('parents',{'changed':'sha'})):
                changed=dict(manifest,**{field:value});target.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):read_fixture(target)
            changed=copy.deepcopy(manifest);changed['parts'][0]['file']='../outside';target.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):read_fixture(target)
            target.write_text(json.dumps(manifest));part=root/manifest['parts'][0]['file'];original=part.read_bytes();part.write_bytes(bytes([original[0]^1])+original[1:])
            with self.assertRaises(ValueError):read_fixture(target)
            part.unlink()
            # A complete dense archive is present, but an invalid manifest
            # must never silently fall back to it.
            with self.assertRaises(FileNotFoundError):read_fixture(target)

    def fixture(self):
        f=dict(loader_pages={},loader_records={},loader_record_keys=[])
        for address,raw in ((0x1000,b'AB'),(0x1004,b'CD')):
            sha=hashlib.sha256(raw).hexdigest();r=dict(address=address,size=2,sha256=sha,pages=[sha]);key=record_id(r)
            f['loader_pages'][sha]=raw.hex();f['loader_records'][key]=r;f['loader_record_keys'].append(key)
        a=dict(registers={'eax':3},xstate='7f03',region_ids=[0,1],maps=[{'address':100}],environment={'LANG':'C'})
        b=dict(registers={'eax':4},xstate='7f03',region_ids=[1,0]);return f,a,b

    def test_lossless_all_fields_pages_owner_order_aliases_and_mapping_gaps(self):
        f,a,b=self.fixture();originals=copy.deepcopy([a,b]);templates={};pack_state(f,a,templates);pack_state(f,b,templates);self.assertEqual(compact_pages(f),2)
        self.assertEqual([unpack_state(f,s)for s in (a,b)],originals)
        first,last=(expand_state(f,s)for s in (a,b));self.assertEqual([data(f,r)for r in first['regions']],[b'AB',b'CD']);self.assertEqual([data(f,r)for r in last['regions']],[b'CD',b'AB'])
        last['regions'][0]['printf_page_ids'].append(0);self.assertEqual(len(f['loader_records'][f['loader_record_keys'][1]]['printf_page_ids']),1)
        m=memory_for(f,first);self.assertEqual(m.read(0x1000,2),b'AB')
        with self.assertRaises(MemoryFault):m.read(0x1002,2)
        m.forget(0x1000,1)
        with self.assertRaises(UnknownMemory):m.read(0x1000,1)

    def test_corrupted_context_fp_manifest_and_update_indices_fail(self):
        f,a,_=self.fixture();pack_state(f,a,{});compact_pages(f)
        mutations=[lambda g,s:g['printf_contexts'][s['printf_context']]['environment'].update(LANG='changed'),lambda g,s:g['printf_xstates'].__setitem__(s['printf_xstate'],'0000'),lambda g,s:g['printf_region_templates'][0].reverse(),lambda g,s:g['loader_record_keys'].reverse(),lambda g,s:s.update(printf_region_template=True),lambda g,s:s.update(printf_region_template=-1),lambda g,s:s.update(printf_region_updates=[[0,0],[0,1]]),lambda g,s:s.update(printf_region_updates=[[1,0],[0,0]]),lambda g,s:s.update(printf_region_updates=[[0,True]])]
        for mutation in mutations:
            g,s=copy.deepcopy((f,a));mutation(g,s)
            with self.assertRaises(ValueError):unpack_state(g,s)

    def test_page_checksums_indices_and_missing_earlier_content_cannot_use_cache(self):
        f,a,_=self.fixture();pack_state(f,a,{});compact_pages(f);r=expand_state(f,a)['regions'][0];self.assertEqual(data(f,r),b'AB');key=f['printf_page_keys'][r['printf_page_ids'][0]]
        g=copy.deepcopy(f);g['printf_pages'][key]=base64.b64encode(zlib.compress(b'ZZ')).decode()
        with self.assertRaises(ValueError):data(g,r)
        g=copy.deepcopy(f);g['printf_pages'].pop(key)
        with self.assertRaises(KeyError):data(g,r)
        for index in (True,-1,2):
            with self.assertRaises(ValueError):data(f,dict(r,printf_page_ids=[index]))
        g,_,_=self.fixture();key=next(iter(g['loader_pages']));g['loader_pages'][key]='ffff'
        with self.assertRaises(ValueError):compact_pages(g)
        # Two versions of the same full page exercise lossless XOR against
        # a full base page, including cache independence when that base is
        # subsequently missing or corrupt.
        g,_,_=self.fixture();raw=bytes(range(256))*16;changed=bytearray(raw);changed[313]^=7;native=[]
        for value in (raw,bytes(changed)):
            sha=hashlib.sha256(value).hexdigest();region=dict(address=0x2000,size=4096,sha256=sha,pages=[sha]);g['loader_pages'][sha]=value.hex();g['loader_records'][record_id(region)]=region;native.append(region)
        compact_pages(g);key=native[1]['sha256'];base=native[0]['sha256'];self.assertTrue(g['printf_pages'][key].startswith(base+':'));self.assertEqual(data(g,native[1]),bytes(changed))
        h=copy.deepcopy(g);h['printf_pages'].pop(base)
        with self.assertRaises(KeyError):data(h,native[1])
        h=copy.deepcopy(g);h['printf_pages'][base]=base64.b64encode(zlib.compress(b'\0'*4096)).decode()
        with self.assertRaises(ValueError):data(h,native[1])


if __name__=='__main__':unittest.main()
