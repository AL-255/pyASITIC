"""Original vfprintf caller phases; formatter execution remains required."""
import collections,copy,hashlib,json,os,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_vfprintf_original as capture
from audit_vfprintf_original import compare,engine,phases,run,selected_indices
from printf_archive import read_fixture
from printf_fixture import data,expand_state,unpack_state,digest_context
from reasitic.memory import UnknownMemory


class VfprintfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=read_fixture(ROOT/'tests/fixtures/vfprintf_original.manifest.json');cls.case=cls.fixture['cases'][0]
        cls.one=dict(cls.case,printf_calls=[cls.case['printf_calls'][0]])
        cls.allocation=next(call for call in cls.case['printf_calls']if any(c['kind']=='malloc'for c in call['children']))

    def test_all_unchanged_histories_and_complete_capture_provenance(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        self.assertEqual(f['vfprintf_provenance']['observer'],capture.OBSERVER)
        self.assertEqual(f['original_sha256'],'72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f')
        self.assertEqual(f['legacy_sha256'],'bca97b602b1eec9f0b591bec0fa4dc5f84f1382636cc8f10094f1da8a3c77d34')
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0];self.assertEqual(f['gdb_commands'],capture.commands(Path(directory)))
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        for key,context in f['printf_contexts'].items():self.assertEqual(key,digest_context(context))
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            for call in c['printf_calls']:
                self.assertEqual(set(call),{'kind','before','after','children','formatter'});self.assertEqual(call['kind'],'vfprintf')
                fmt=call['formatter'];self.assertEqual(set(fmt),{'before','after','children_start','children_end'})
                self.assertTrue(0<=fmt['children_start']<=fmt['children_end']<=len(call['children']))
                for a,b in ((call['before'],call['after']),(fmt['before'],fmt['after'])):self.assertEqual(a['registers']['esp']+4,b['registers']['esp'])
                a=unpack_state(f,call['before']);self.assertLessEqual(set(a['environment']),{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'})
                for child in call['children']:
                    self.assertEqual(set(child),{'kind','before','after'});self.assertEqual(child['before']['esp']+4,child['after']['esp'])

    def test_every_native_caller_memory_heap_register_fp_and_helper_target(self):
        f=self.fixture;report=run(f,shard=int(os.environ.get('PYASITIC_VFPRINTF_SHARD','1')),shards=int(os.environ.get('PYASITIC_VFPRINTF_SHARDS','1')))
        if target:=os.environ.get('PYASITIC_VFPRINTF_REPORT'):Path(target).write_text(json.dumps(report,indent=2)+'\n')
        self.assertEqual(report['differences'],0);calls=[c for i in report['case_indices']for c in f['cases'][i]['printf_calls']]
        self.assertEqual(report['parent_calls'],len(calls));self.assertEqual(report['calls_checked'],2*len(calls));self.assertEqual(report['registers_checked'],34*len(calls))
        self.assertEqual(report['formatter_calls_pending'],len(calls),'Caller parity cannot declare formatter work complete')
        self.assertEqual(report['formatter_children_pending'],sum(c['formatter']['children_end']-c['formatter']['children_start']for c in calls))
        self.assertEqual(report['fp_bytes_checked'],sum(len(unpack_state(f,p)['xstate'])//2 for c in calls for p in (c['formatter']['before'],c['after'])))
        children=sum(c['formatter']['children_start']+len(c['children'])-c['formatter']['children_end']for c in calls)
        self.assertEqual(report['children_checked'],children);self.assertEqual(report['child_registers_checked'],34*children)
        words=[(f['loader_records'][key]['size']+3)//4 for key in f['loader_record_keys']]
        self.assertEqual(report['words_checked'],sum(words[i]for c in calls for p in (c['formatter']['before'],c['after'])for i in unpack_state(f,p)['region_ids']))

    def test_later_phase_memory_register_fp_heap_and_helpers_are_assertions(self):
        f=dict(self.fixture,loader_regions={});c=copy.deepcopy(self.one);call=c['printf_calls'][0]
        for parent in (call,call['formatter']):
            for phase in ('before','after'):parent[phase]=copy.deepcopy(expand_state(f,parent[phase]))
        b=call['formatter']['before'];address=b['registers']['esp']-8;r=next(x for x in b['regions']if x['address']<=address<x['address']+x['size'])
        raw=bytearray(data(f,r));raw[address-r['address']]^=1;key=hashlib.sha256(raw).hexdigest();f['loader_regions'][key]=raw.hex();r.pop('printf_page_ids',None);r.pop('pages',None);r['sha256']=key
        b['registers']['eax']^=1;b['xstate']='00'+b['xstate'][2:];b['heap']['top']+=16
        call['children'][0]['before']['ebx']^=1;call['children'][0]['after']['ecx']^=1
        counts=collections.Counter(d['kind']for d in compare(f,c)['differences'])
        self.assertEqual(counts,{'printf-memory-word':1,'printf-register':1,'printf-fp-byte':1,'state':1,'printf-child-register':2})
        b['regions'].pop();self.assertIn('printf-region-owners',[d['kind']for d in compare(f,c)['differences']])

    def test_earlier_variadic_pointer_and_mode_flags_reach_formatter(self):
        a=expand_state(self.fixture,self.one['printf_calls'][0]['before']);m,storage=engine(self.fixture,a);r=a['registers'];s=r['esp'];m.put_u32(s+12,0x12345678);m.put_u32(s+16,3)
        result=storage.before_formatter(r);self.assertEqual(m.u32(result['esp']+12),0x12345678);self.assertEqual(m.u32(result['esp']+16),3)
        self.assertEqual(m.u32(result['esp']+8),m.u32(s+8));self.assertEqual(m.u32(result['esp']+4),s-188)

    def test_first_narrow_call_orients_file_before_buffer_setup(self):
        a=expand_state(self.fixture,self.allocation['before']);m,storage=engine(self.fixture,a);r=a['registers'];file=m.u32(r['esp']+4)
        self.assertEqual(m.u32(file+104),0);storage.before_formatter(r);self.assertEqual(m.u32(file+104),0xffffffff)
        self.assertEqual(m.u32(file+28),0,'Setup does not allocate the later output buffer')

    def test_no_default_formatter_or_later_snapshot_substitution(self):
        a=expand_state(self.fixture,self.one['printf_calls'][0]['before']);m,storage=engine(self.fixture,a)
        with self.assertRaisesRegex(NotImplementedError,'parser and numeric formatter'):storage.call(a['registers'])

    def test_callback_uses_same_memory_and_suffix_count(self):
        a=expand_state(self.fixture,self.one['printf_calls'][0]['before']);m,storage=engine(self.fixture,a);seen=[]
        def formatter(r):
            # A test-only callback exercises the connection contract, not a
            # formatting implementation or a native comparison substitute.
            seen.append(dict(r));buf=m.u32(r['esp']+4);p=m.u32(buf+4);m.write(p,b'X');m.put_u32(buf+4,p+1)
            return dict(r,esp=r['esp']+4,eip=m.u32(r['esp']))
        result=storage.call(a['registers'],formatter);self.assertEqual(len(seen),1);self.assertEqual(result['eax'],1)
        self.assertEqual(result['esp'],a['registers']['esp']+4)
        for name in ('ebp','edi','esi','ebx'):self.assertEqual(result[name],a['registers'][name])

    def test_missing_earlier_controls_and_suffix_canary_fail(self):
        call=self.one['printf_calls'][0];a=expand_state(self.fixture,call['before'])
        for name in ('compat','canary'):
            m,storage=engine(self.fixture,a);m.forget(storage.got+0x11c if name=='compat'else storage.tls+20,4)
            with self.subTest(name=name),self.assertRaises(UnknownMemory):storage.before_formatter(a['registers'])
        c=expand_state(self.fixture,call['formatter']['after']);m,storage=engine(self.fixture,dict(a,**c));r=c['registers'];local=r['esp']+32;m.put_u32(local+188,m.u32(local+188)^1)
        with self.assertRaisesRegex(ValueError,'canary'):storage.after_formatter(r)

    def test_unimplemented_locked_orientation_and_error_paths_are_explicit(self):
        a=expand_state(self.fixture,self.one['printf_calls'][0]['before'])
        for name in ('locked','wide','null','readonly'):
            m,storage=engine(self.fixture,a);r=a['registers'];s=r['esp'];file=m.u32(s+4)
            if name=='locked':m.write(file+60,b'\x80')
            elif name=='wide':m.put_u32(file+104,1)
            elif name=='null':m.put_u32(s+8,0)
            else:m.put_u32(file,m.u32(file)|8)
            with self.subTest(name=name),self.assertRaises(NotImplementedError):storage.before_formatter(r)

    def test_missing_or_invalid_formatter_boundaries_never_pass(self):
        for name in ('missing','indices'):
            c=copy.deepcopy(self.one);call=c['printf_calls'][0]
            if name=='missing':del call['formatter']['after'];self.assertIn('vfprintf-missing-boundary',[d['kind']for d in compare(self.fixture,c)['differences']])
            else:
                call['formatter']['children_end']=-1
                with self.assertRaisesRegex(ValueError,'indices'):phases(self.fixture,c)

    def test_shards_partition_all_histories(self):
        count=len(self.fixture['cases'])
        for shards in (1,2,8,count):self.assertEqual(sorted(i for shard in range(1,shards+1)for i in selected_indices(count,shard,shards)),list(range(count)))


if __name__=='__main__':unittest.main()
