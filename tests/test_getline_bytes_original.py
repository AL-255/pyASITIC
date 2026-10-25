"""Complete scalar native search/copy operations and input causality."""
import collections,copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_getline_bytes_original as capture
from audit_getline_bytes_original import compare,engine
from audit_loader_lookup_original import data,memory_for
from getline_fixture import expand_case,expand_state
from reasitic.memory import MemoryFault,UnknownMemory


class GetlineBytesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/getline_bytes_original.json.gz').read_bytes()))
        cls.case=next(c for c in cls.fixture['cases']if c['label']=='prelude/fft/16/8'and c['cache_mode']=='cold')

    def test_all_original_histories_complete_owners_and_provenance(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        self.assertEqual(f['getline_bytes_provenance']['observer'],capture.OBSERVER)
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0];self.assertEqual(f['gdb_commands'],capture.commands(Path(directory)))
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            for call in c['byte_calls']:
                self.assertEqual(set(call),{'kind','before','after'});a,b=call['before'],call['after']
                self.assertEqual(a['registers']['esp']+4,b['registers']['esp'])
                self.assertLessEqual(set(a['environment']),{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'})
                for point in (a,b):
                    for region in expand_state(f,point)['regions']:data(f,region)
        self.assertEqual(collections.Counter(c['signal']for c in f['cases']),{0:132,11:1,6:1})
        self.assertEqual(collections.Counter(x['kind']for c in f['cases']for x in c['byte_calls']),{'memchr':134,'memcpy':134})

    def test_independent_cpu_probe_defined_flags_and_undefined_af(self):
        cpu=self.fixture['integer_cpu'];self.assertEqual(cpu['probe'],capture.CPU_PROBE);rows=cpu['observations'];self.assertEqual(len(rows),24)
        for i,r in enumerate(rows):
            value=r['input']>>1;expected=(r['input']&1)|(int(not value)<<6)|((value>>31)<<7)|(int((value&255).bit_count()%2==0)<<2)|((r['input']>>31)<<11)
            self.assertEqual(r['result'],value);self.assertEqual(r['flags_after']&0x8c5,expected);self.assertEqual(r['flags_before']&16,(i//12)*16)
            self.assertEqual(r['flags_after']&16,r['flags_before']&16 if cpu['shr1_af']=='preserve'else cpu['shr1_af'])

    def test_every_native_region_register_and_fp_byte(self):
        reports=[compare(self.fixture,c)for c in self.fixture['cases']];self.assertEqual([r['differences']for r in reports],[[]]*134)
        for key,value in (('calls_checked',268),('words_checked',63688292),('registers_checked',4556),('fp_bytes_checked',653920)):
            self.assertEqual(sum(r[key]for r in reports),value)

    def test_later_targets_cannot_supply_search_copy_results(self):
        f=dict(self.fixture,loader_regions={});c=copy.deepcopy(expand_case(f,self.case));b=c['byte_calls'][-1]['after'];address=b['registers']['esp']-8
        region=next(r for r in b['regions']if r['address']<=address<r['address']+r['size']);raw=bytearray(data(f,region));raw[address-region['address']]^=1;key=hashlib.sha256(raw).hexdigest();f['loader_regions'][key]=raw.hex();region.pop('pages');region['sha256']=key
        b['registers']['eax']^=1;b['xstate']='00'+b['xstate'][2:]
        self.assertEqual(collections.Counter(d['kind']for d in compare(f,c)['differences']),{'getline-bytes-memory-word':1,'getline-bytes-register':1,'getline-bytes-fp-byte':1})
        b['regions'].pop();self.assertIn('getline-bytes-region-owners',[d['kind']for d in compare(f,c)['differences']])

    def test_bounded_search_does_not_read_past_the_last_word(self):
        case=next(c for c in self.fixture['cases']if c['label']=='square/32/coarse'and c['cache_mode']=='cold');a=case['byte_calls'][0]['before'];m,op=engine(self.fixture,a);r=a['registers'];p=m.u32(r['esp']+4);self.assertEqual(p&3,3)
        m.put_u32(r['esp']+12,5);m.write(p,b'ABCDE');m.forget(p+5,4)
        self.assertEqual(op.memchr(r)['eax'],0)
        m,op=engine(self.fixture,a);m.put_u32(r['esp']+12,5);m.write(p,b'ABCD\n');self.assertEqual(op.memchr(r)['eax'],p+4)

    def test_copy_uses_source_forward_byte_and_word_order(self):
        a=self.case['byte_calls'][-1]['before'];m,op=engine(self.fixture,a);r=a['registers'];s=r['esp'];p=m.u32(s+8)
        m.write(p,b'abcdefghi');m.put_u32(s+4,p+1);m.put_u32(s+12,5)
        result=op.memcpy(r);self.assertEqual(m.read(p,9),b'aaacdeghi');self.assertEqual(result['eax'],p+1)
        m,op=engine(self.fixture,a);m.forget(m.u32(s+8),1)
        with self.assertRaises(UnknownMemory):op.memcpy(r)

    def test_region_union_optimization_keeps_gaps_and_manifest_integrity(self):
        blobs={};regions=[]
        for address,raw in ((0x1000,b'abcd'),(0x1002,b'cdEF'),(0x1008,b'gh')):
            key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();regions.append(dict(address=address,size=len(raw),sha256=key))
        m=memory_for(dict(loader_regions=blobs),dict(regions=regions));self.assertEqual(m.read(0x1000,6),b'abcdEF')
        with self.assertRaises(MemoryFault):m.read(0x1005,4)
        f=dict(self.fixture,loader_records=dict(self.fixture['loader_records']));a=self.case['byte_calls'][0]['before'];key=f['loader_record_keys'][a['region_ids'][0]];f['loader_records'][key]=dict(f['loader_records'][key],address=0)
        with self.assertRaisesRegex(ValueError,'manifest'):expand_state(f,a)
        a=copy.deepcopy(a);a['region_ids'][0]=-1
        with self.assertRaisesRegex(ValueError,'manifest'):expand_state(self.fixture,a)


if __name__=='__main__':unittest.main()
