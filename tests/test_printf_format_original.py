"""Every original formatter target stays required, including unfinished paths."""
import collections,copy,hashlib,json,os,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_printf_format_original as capture
from audit_printf_format_original import compare,engine,run,selected_indices
from printf_archive import read_fixture
from printf_fixture import expand_state,unpack_state,digest_context
from capture_getline_bytes_original import CPU_PROBE
from reasitic.memory import Memory,UnknownMemory
from reasitic.heap import AddressSpace
from reasitic.strlen_storage import StrlenStorage


class PrintfFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=read_fixture(os.environ.get('PYASITIC_PRINTF_FORMAT_FIXTURE',ROOT/'tests/fixtures/printf_format_original.manifest.json'))
        cls.case=cls.fixture['cases'][0];cls.one=dict(cls.case,printf_calls=[cls.case['printf_calls'][0]])

    def test_all_histories_and_complete_earlier_capture_provenance(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        calls=[call for c in f['cases']for call in c['printf_calls']]
        self.assertEqual(len(calls),4105);self.assertEqual(sum(len(c['children'])for c in calls),104036)
        self.assertEqual(collections.Counter(c['signal']for c in f['cases']),{0:132,11:1,6:1})
        self.assertEqual(collections.Counter(unpack_state(f,c['before'])['buffer_mode']for c in calls),{4:3973,2:132})
        self.assertEqual(f['printf_format_provenance']['observer'],capture.OBSERVER)
        self.assertEqual(f['integer_cpu']['probe'],CPU_PROBE)
        self.assertEqual(f['original_sha256'],'72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f')
        self.assertEqual(f['legacy_sha256'],'bca97b602b1eec9f0b591bec0fa4dc5f84f1382636cc8f10094f1da8a3c77d34')
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0];self.assertEqual(f['gdb_commands'],capture.commands(Path(directory)))
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        for key,context in f['printf_contexts'].items():self.assertEqual(key,digest_context(context))
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            for call in c['printf_calls']:
                self.assertEqual(set(call),{'kind','before','after','children','initial_write'});self.assertEqual(call['kind'],'format')
                a=unpack_state(f,call['before']);self.assertEqual(a['registers']['esp']+4,call['after']['registers']['esp'])
                self.assertLessEqual(set(a['environment']),{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'})
                self.assertEqual(a['format_inputs']['pthread_size'],1216)
                tls=a['format_inputs']['static_tls'];self.assertEqual(tls['tcb_size'],1216)
                self.assertGreaterEqual(tls['size'],tls['tcb_size']);self.assertEqual(tls['address']+tls['size'],a['tls_base']+tls['tcb_size'])
                self.assertEqual(tls['size_address'],tls['loader_ro']+832)
                self.assertTrue(any(r['address']==tls['address']and r['size']==tls['size']for r in expand_state(f,call['before'])['regions']))
                libc=next(e for e in a['format_inputs']['elf_data']if e['path'].endswith('/libc.so.6'))
                self.assertEqual(libc['elf_sha256'],'e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0')
                # This pinned libc has one merged .got, no .got.plt section.
                # Require its complete actual section table, not an invented
                # section or a weaker subset check. Other ELF objects retain
                # their own .got.plt sections when those exist.
                self.assertEqual([(s['name'],s['offset'],s['size'])for s in libc['sections']],
                    [('.rodata',0x1a9000,0x25350),('.data.rel.ro',0x22e5a0,0x178c),('.got',0x22fe34,0x1cc),('.data',0x230000,0xeb8),('.bss',0x230ec0,0x99fc)])
                self.assertTrue(0<=call['initial_write']['children_start']<=len(call['children']))
                for child in call['children']:
                    self.assertEqual(set(child),{'kind','before','after'});self.assertEqual(child['before']['esp']+4,child['after']['esp'])

    def test_every_prefix_and_complete_formatter_remain_strict(self):
        f=self.fixture;shard=int(os.environ.get('PYASITIC_PRINTF_FORMAT_SHARD','1'));shards=int(os.environ.get('PYASITIC_PRINTF_FORMAT_SHARDS','1'))
        reports=[run(f,prefix=prefix,shard=shard,shards=shards)for prefix in (True,False)]
        if target:=os.environ.get('PYASITIC_PRINTF_FORMAT_REPORT'):Path(target).write_text(json.dumps(dict(prefix=reports[0],complete=reports[1]),indent=2)+'\n')
        required=sum(len(f['cases'][i]['printf_calls'])for i in reports[0]['case_indices'])
        for report in reports:
            with self.subTest(scope=report['scope']):
                self.assertEqual(report['calls_required'],required)
                self.assertEqual(report['differences'],0,'All conversions and kernel-owned TLS targets stay required')
                self.assertEqual(report['calls_checked'],required)

    def test_changed_earlier_string_argument_reaches_real_output(self):
        a=expand_state(self.fixture,self.one['printf_calls'][0]['before']);m,storage=engine(self.fixture,a);r=a['registers'];s=r['esp']
        buf=m.u32(s+4);fmt=m.u32(s+8);args=m.u32(s+12);source=m.u32(args);self.assertEqual(m.read(fmt,4),b'\n%s\0')
        pointer=m.u32(buf+4);m.write(source,b'NEW\0');result=storage.format(r)
        self.assertEqual(m.read(pointer,4),b'\nNEW');self.assertEqual(m.u32(buf+4),pointer+4)
        self.assertEqual(result['esp'],s+4);self.assertEqual(result['eax'],0)
        self.assertEqual(next(c['after']['eax']for c in storage.children if c['kind']=='strlen-ia32'),3)

    def test_missing_earlier_got_format_and_string_bytes_fail(self):
        a=expand_state(self.fixture,self.one['printf_calls'][0]['before'])
        for which in ('got','format','string'):
            m,storage=engine(self.fixture,a);r=a['registers'];s=r['esp']
            address=storage.got+0x16c if which=='got'else m.u32(s+8)if which=='format'else m.u32(m.u32(s+12))
            m.forget(address,4 if which=='got'else 1)
            with self.subTest(which=which),self.assertRaises(UnknownMemory):storage.format(r)

    def test_actual_float_state_is_produced_and_missing_earlier_tls_fails(self):
        call=self.case['printf_calls'][9];a=expand_state(self.fixture,call['before']);b=expand_state(self.fixture,call['after']);m,storage=engine(self.fixture,a)
        result=storage.format(a['registers']);self.assertEqual(result,b['registers']);self.assertEqual(storage.xstate,bytes.fromhex(b['xstate']))
        self.assertNotEqual(storage.xstate,bytes.fromhex(a['xstate']),'Floating execution must produce the changed native FP slots/status')
        self.assertEqual(storage.children,call['children'])
        m,storage=engine(self.fixture,a);slot=(a['tls_base']+m.u32(storage.got+0x90))&0xffffffff;m.forget(slot,4)
        with self.assertRaises(UnknownMemory):storage.format(a['registers'])

    def test_float_arguments_are_computed_and_earlier_fp_is_required(self):
        a=expand_state(self.fixture,self.case['printf_calls'][9]['before']);m,storage=engine(self.fixture,a);s=a['registers']['esp'];buf=m.u32(s+4);pointer=m.u32(buf+4);args=m.u32(s+12)
        m.write(args,bytes.fromhex('000000000000f43f'));storage.format(a['registers']);self.assertIn(b'1.25',m.read(pointer,m.u32(buf+4)-pointer))
        m,storage=engine(self.fixture,a);storage.xstate=None
        with self.assertRaisesRegex(ValueError,'actual earlier XSAVE'):storage.format(a['registers'])

    def test_target_changes_never_disappear_behind_unfinished_conversions(self):
        f=self.fixture;c=copy.deepcopy(self.one);call=c['printf_calls'][0];b=expand_state(f,call['after']);call['after']=b
        b['registers']['eax']^=1;b['xstate']='00'+b['xstate'][2:];call['children'][0]['after']['ecx']^=1
        kinds=[d['kind']for d in compare(f,c)['differences']]
        for kind in ('printf-register','printf-fp-byte','printf-child-register'):self.assertIn(kind,kinds)

    def test_missing_boundary_and_return_are_required_failures(self):
        c=copy.deepcopy(self.one);del c['printf_calls'][0]['initial_write'];self.assertIn('format-missing-initial-write',[d['kind']for d in compare(self.fixture,c,prefix=True)['differences']])
        c=copy.deepcopy(self.one);del c['printf_calls'][0]['after'];self.assertIn('printf-missing-return',[d['kind']for d in compare(self.fixture,c)['differences']])
        c=copy.deepcopy(self.one);c['printf_calls'][0]['initial_write']['children_start']=-1
        with self.assertRaisesRegex(ValueError,'boundary'):compare(self.fixture,c,prefix=True)

    def test_shards_partition_every_history_without_conversion_filters(self):
        count=len(self.fixture['cases'])
        for shards in (1,2,8,count):
            if shards<=count:self.assertEqual(sorted(i for shard in range(1,shards+1)for i in selected_indices(count,shard,shards)),list(range(count)))


class ScalarLengthTests(unittest.TestCase):
    def state(self):
        m=Memory(AddressSpace([dict(start=0x1000,end=0x5000)]));m.zero(0x1000,0x4000)
        r=dict(eax=17,ebx=29,ecx=0xabcdef01,edx=23,esi=31,edi=37,ebp=41,esp=0x4000,eip=0xbc470,eflags=0x202)
        m.put_u32(r['esp'],0x12345678);return m,r,StrlenStorage(m,libc_base=0,shr1_af=0)

    def test_alignment_lengths_and_bounded_nonterminated_inputs(self):
        for offset in range(4):
            for length in (0,1,2,3,4,7,15,31,75):
                m,r,storage=self.state();p=0x1100+offset;m.write(p,b'x'*length+b'\0');m.put_u32(r['esp']+4,p)
                result=storage.length(r);self.assertEqual(result['eax'],length)
                for key in ('ebx','esi','edi','ebp'):self.assertEqual(result[key],r[key])
                for limit in (0,1,3,4,13,80):
                    m,r,storage=self.state();m.put_u32(r['esp']+4,p);m.put_u32(r['esp']+8,limit);m.write(p,b'x'*limit);m.forget(p+limit,32)
                    result=storage.bounded(dict(r,eip=0xbb390));self.assertEqual(result['eax'],limit)

    def test_unknown_aligned_padding_is_not_fabricated(self):
        m,r,storage=self.state();p=0x1100;m.put_u32(r['esp']+4,p);m.write(p,b'x\0');m.forget(p+2,2)
        with self.assertRaises(UnknownMemory):storage.length(r)


if __name__=='__main__':unittest.main()
