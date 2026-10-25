"""Complete native fflush and write effects, without returned-count inputs."""
import collections,copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_flush_storage_original as capture
from audit_flush_storage_original import compare,engine
from audit_loader_lookup_original import data
from getline_fixture import expand_state
from reasitic.memory import UnknownMemory


class FlushStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/flush_storage_original.json.gz').read_bytes()))
        cls.case=next(c for c in cls.fixture['cases']if c['label']=='prelude/fft/16/8'and c['cache_mode']=='cold')

    def test_all_histories_and_complete_guarded_native_boundaries(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        self.assertEqual(f['flush_storage_provenance']['observer'],capture.OBSERVER)
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0];self.assertEqual(f['gdb_commands'],capture.commands(Path(directory)))
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            for call in c['flush_calls']:
                self.assertEqual(set(call),{'before','after','writes'});a,b=call['before'],call['after'];self.assertEqual(a['registers']['esp']+4,b['registers']['esp'])
                self.assertLessEqual(set(a['environment']),{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'})
                for point in (a,b):
                    for region in expand_state(f,point)['regions']:data(f,region)
                for write in call['writes']:self.assertEqual(write['returned'],write['count'])
        self.assertEqual(collections.Counter(c['signal']for c in f['cases']),{0:132,11:1,6:1})
        self.assertEqual(sum(not c['flush_calls']for c in f['cases']),1)

    def test_every_native_region_register_fp_byte_and_write(self):
        reports=[compare(self.fixture,c)for c in self.fixture['cases']];self.assertEqual([r['differences']for r in reports],[[]]*134)
        for key,value in (('calls_checked',414),('words_checked',98167038),('registers_checked',7038),('fp_bytes_checked',1010160),('writes_checked',413),('write_bytes_checked',198537)):
            self.assertEqual(sum(r[key]for r in reports),value)

    def test_later_memory_register_fp_and_write_counts_are_assertions(self):
        f=dict(self.fixture,loader_regions={});c=copy.deepcopy(self.case)
        for call in c['flush_calls']:
            call['before']=expand_state(f,call['before']);call['after']=expand_state(f,call['after'])
        b=c['flush_calls'][-1]['after'];address=b['registers']['esp']-8;r=next(r for r in b['regions']if r['address']<=address<r['address']+r['size']);raw=bytearray(data(f,r));raw[address-r['address']]^=1;key=hashlib.sha256(raw).hexdigest();f['loader_regions'][key]=raw.hex();r.pop('pages');r['sha256']=key
        b['registers']['eax']^=1;b['xstate']='00'+b['xstate'][2:];c['flush_calls'][-1]['writes'][0]['returned']-=1
        self.assertEqual(collections.Counter(d['kind']for d in compare(f,c)['differences']),{'flush-memory-word':1,'flush-register':1,'flush-fp-byte':1,'flush-write':1})
        b['regions'].pop();self.assertIn('flush-region-owners',[d['kind']for d in compare(f,c)['differences']])

    def test_pending_earlier_bytes_determine_the_emitted_write(self):
        a=self.case['flush_calls'][4]['before'];m,storage=engine(self.fixture,a);r=a['registers'];file=m.u32(r['esp']+4);buffer=m.u32(file+16)
        m.write(buffer,b'XYZ');m.put_u32(file+20,buffer+3);result=storage.flush(r)
        self.assertEqual(storage.writes,[dict(fd=m.u32(file+56),address=buffer,count=3,data=b'XYZ'.hex(),returned=3)])
        self.assertEqual(m.u32(file+20),m.u32(file+28));self.assertEqual(result['eax'],0)

    def test_unused_incoming_volatile_registers_do_not_supply_child_state(self):
        for call in self.case['flush_calls'][4:]:
            a=call['before'];m,one=engine(self.fixture,a);expected=one.flush(a['registers']);other_m,two=engine(self.fixture,a)
            actual=two.flush(dict(a['registers'],eax=0x12345678,ecx=0x87654321,edx=0xabcdef01))
            self.assertEqual(actual,expected);self.assertEqual(two.writes,one.writes)
            for region in expand_state(self.fixture,a)['regions']:self.assertEqual(m.read(region['address'],region['size']),other_m.read(region['address'],region['size']))

    def test_missing_earlier_foreign_vtable_guard_cannot_use_return_snapshot(self):
        a=self.case['flush_calls'][4]['before'];m,storage=engine(self.fixture,a);m.forget(storage.got+0x1a30,4)
        with self.assertRaises(UnknownMemory):storage.flush(a['registers'])

    def test_unread_input_seek_is_an_explicit_unimplemented_path(self):
        a=self.case['flush_calls'][5]['before'];m,storage=engine(self.fixture,a);file=m.u32(a['registers']['esp']+4);m.put_u32(file+8,m.u32(file+4)+1)
        with self.assertRaisesRegex(NotImplementedError,'seek syscall'):storage.flush(a['registers'])


if __name__=='__main__':unittest.main()
