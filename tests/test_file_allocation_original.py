"""Complete stat/buffer caller comparisons and independent external inputs."""
import collections,copy,gzip,hashlib,json,re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_file_allocation_original as capture
from audit_file_allocation_original import compare,engine
from audit_loader_lookup_original import data


class FileAllocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/file_allocation_original.json.gz').read_bytes()))
        cls.case=next(c for c in cls.fixture['cases']if c['allocation_calls'])

    def test_all_histories_boundaries_provenance_and_guarded_environments(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        self.assertEqual(f['file_allocation_provenance']['observer'],capture.OBSERVER)
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0];self.assertEqual(f['gdb_commands'],capture.commands(Path(directory)))
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            for call in c['allocation_calls']:
                self.assertEqual(set(call),{'entry','malloc','allocated','return'});a=call['entry']
                self.assertEqual(a['profile']['statx']['query_mask'],0x7ff);self.assertNotIn('raw',a['profile']['statx'])
                self.assertLessEqual(set(a['environment']),{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'})
                s=a['registers']['esp'];stack=next(r for r in a['regions']if r['address']<=s<r['address']+r['size'])
                for part in data(f,stack).split(b'\0'):
                    key=re.match(rb'^([A-Za-z_][A-Za-z0-9_]*)=',part)
                    if key:self.assertIsNone(re.search(rb'KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL',key.group(1),re.I))
                for point in call.values():
                    for r in point['regions']:data(f,r)
        self.assertEqual(collections.Counter(c['signal']for c in f['cases']),{0:132,11:1,6:1})
        self.assertEqual(sum(not c['allocation_calls']for c in f['cases']),133)

    def test_complete_native_memory_register_and_fp_boundaries(self):
        reports=[compare(self.fixture,c)for c in self.fixture['cases']]
        self.assertEqual([r['differences']for r in reports],[[]]*134)
        for key,value in (('operations_checked',2),('words_checked',333348),('registers_checked',34),('fp_bytes_checked',4880)):
            self.assertEqual(sum(r[key]for r in reports),value)

    def test_later_stat_buffer_register_and_fp_mutations_are_not_inputs(self):
        f=copy.deepcopy(self.fixture);c=copy.deepcopy(self.case);b=c['allocation_calls'][0]['malloc'];s=b['registers']['esp'];address=s+20
        r=next(r for r in b['regions']if r['address']<=address<r['address']+r['size']);raw=bytearray(data(f,r));raw[address-r['address']]^=1;key=hashlib.sha256(raw).hexdigest();f['loader_regions'][key]=raw.hex();r['sha256']=key
        b['registers']['eax']^=1;b['xstate']='00'+b['xstate'][2:]
        self.assertEqual(collections.Counter(d['kind']for d in compare(f,c)['differences']),{'file-allocation-memory-word':1,'file-allocation-register':1,'file-allocation-fp-byte':1})
        b['regions'].pop();self.assertIn('file-allocation-region-owners',[d['kind']for d in compare(f,c)['differences']])

    def test_earlier_inode_and_time64_fields_drive_both_stat_records(self):
        call=self.case['allocation_calls'][0];ctx=copy.deepcopy(call['entry']);x=ctx['profile']['statx']['fields'];x['ino']=0x123456789abcdef0;x['ctime']=dict(sec=0x100000001,nsec=456)
        m,storage=engine(self.fixture,ctx,ctx);regs=storage.before_malloc(ctx['registers']);out=regs['esp']+20
        self.assertEqual(int.from_bytes(m.read(out+8,8),'little'),x['ino'])
        self.assertEqual(int.from_bytes(m.read(out+92,8),'little'),x['ctime']['sec']);self.assertEqual(m.u32(out+100),456)
        # Kernel statx lies below the independent libc stat destination.
        statx=out-360
        self.assertEqual(int.from_bytes(m.read(statx+32,8),'little'),x['ino'])
        self.assertEqual(m.read(out+72,4)+m.read(out+88,4)+m.read(out+104,4),b'\0'*12)

    def test_buffer_pointer_is_the_earlier_malloc_return(self):
        call=self.case['allocation_calls'][0];a=call['allocated'];m,storage=engine(self.fixture,a,call['entry']);regs=dict(a['registers'],eax=0x12345000)
        file=regs['esi'];capacity=regs['ebp'];result=storage.after_malloc(regs)
        self.assertEqual(m.u32(file+28),regs['eax']);self.assertEqual(m.u32(file+32),regs['eax']+capacity)
        self.assertEqual(result['eax'],1)
