"""Complete native read targets and independent file/position causality."""
import collections,copy,gzip,hashlib,json,re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_read_storage_original as capture
from audit_read_storage_original import compare,engine
from audit_loader_lookup_original import data
from reasitic.memory import UnknownMemory


class ReadStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/read_storage_original.json.gz').read_bytes()))
        cls.case=next(c for c in cls.fixture['cases']if c['read_calls'])

    def test_every_original_history_complete_capture_and_environment(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        self.assertEqual(f['read_storage_provenance']['observer'],capture.OBSERVER)
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0];self.assertEqual(f['gdb_commands'],capture.commands(Path(directory)))
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            for call in c['read_calls']:
                self.assertEqual(set(call),{'before','after'});a=call['before']
                self.assertEqual(bytes.fromhex(a['external_stdin']['data']),c['stdin'].encode());self.assertEqual(a['external_stdin']['position'],0)
                self.assertLessEqual(set(a['environment']),{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'})
                for point in call.values():
                    for region in point['regions']:data(f,region)
                s=a['registers']['esp'];stack=next(r for r in a['regions']if r['address']<=s<r['address']+r['size'])
                for part in data(f,stack).split(b'\0'):
                    key=re.match(rb'^([A-Za-z_][A-Za-z0-9_]*)=',part)
                    if key:self.assertIsNone(re.search(rb'KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL',key.group(1),re.I))
        self.assertEqual(collections.Counter(c['signal']for c in f['cases']),{0:132,11:1,6:1})
        self.assertEqual(sum(not c['read_calls']for c in f['cases']),133)

    def test_every_native_region_register_fp_byte_and_offset(self):
        reports=[compare(self.fixture,c)for c in self.fixture['cases']]
        self.assertEqual([r['differences']for r in reports],[[]]*134)
        for key,value in (('calls_checked',1),('words_checked',201467),('registers_checked',17),('fp_bytes_checked',2440),('positions_checked',1),('bytes_read',5)):
            self.assertEqual(sum(r[key]for r in reports),value)

    def test_later_read_buffer_register_fp_and_position_are_assertions(self):
        f=copy.deepcopy(self.fixture);c=copy.deepcopy(self.case);call=c['read_calls'][0];b=call['after'];a=call['before'];m,_=engine(f,a);address=m.u32(a['registers']['esp']+8)+8
        region=next(r for r in b['regions']if r['address']<=address<r['address']+r['size']);raw=bytearray(data(f,region));raw[address-region['address']]^=1;key=hashlib.sha256(raw).hexdigest();f['loader_regions'][key]=raw.hex();region['sha256']=key
        b['registers']['eax']^=1;b['xstate']='00'+b['xstate'][2:];b['position']+=1
        self.assertEqual(collections.Counter(d['kind']for d in compare(f,c)['differences']),{'read-memory-word':1,'read-register':1,'read-fp-byte':1,'read-position':1})
        b['regions'].pop();self.assertIn('read-region-owners',[d['kind']for d in compare(f,c)['differences']])

    def test_earlier_file_bytes_offset_and_caller_registers_drive_read(self):
        a=self.case['read_calls'][0]['before'];m,storage=engine(self.fixture,a);r=dict(a['registers'],ebx=0x12345678,ebp=0x76543210);s=r['esp'];buffer=m.u32(s+8);capacity=m.u32(s+12);tail=m.read(buffer+5,capacity-5)
        result=storage.read(r,b'A1234\n',1)
        self.assertEqual(result['data'],b'1234\n');self.assertEqual(result['position'],6);self.assertEqual(m.read(buffer,5),b'1234\n');self.assertEqual(m.read(buffer+5,capacity-5),tail)
        self.assertEqual(m.u32(s-12),r['ebx']);self.assertEqual(m.u32(s-44),r['ebp'])
        self.assertEqual(result['registers']['ebx'],r['ebx']);self.assertEqual(result['registers']['ebp'],r['ebp'])

    def test_missing_earlier_vdso_cannot_use_later_memory(self):
        a=self.case['read_calls'][0]['before'];m,storage=engine(self.fixture,a);m.forget(m.u32(storage.tls+16),32)
        with self.assertRaises(UnknownMemory):storage.read(a['registers'],bytes.fromhex(a['external_stdin']['data']),a['external_stdin']['position'])

    def test_eof_read_preserves_buffer_and_descriptor_position(self):
        a=self.case['read_calls'][0]['before'];m,storage=engine(self.fixture,a);r=a['registers'];buffer=m.u32(r['esp']+8);capacity=m.u32(r['esp']+12);before=m.read(buffer,capacity)
        result=storage.read(r,b'',7)
        self.assertEqual(result['data'],b'');self.assertEqual(result['position'],7);self.assertEqual(result['registers']['eax'],0);self.assertEqual(m.read(buffer,capacity),before)


if __name__=='__main__':unittest.main()
