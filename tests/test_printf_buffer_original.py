"""Complete native printf buffer write source and every memcpy boundary."""
import collections,copy,hashlib,json,os,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_printf_buffer_original as capture
from audit_printf_buffer_original import compare,engine,run,selected_indices
from getline_fixture import record_id
from printf_fixture import data,expand_state,unpack_state,digest_context
from capture_getline_bytes_original import CPU_PROBE
from reasitic.memory import Memory,UnknownMemory
from reasitic.heap import AddressSpace
from reasitic.printf_buffer import PrintfBuffer
from printf_archive import read_fixture


class PrintfBufferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=read_fixture(ROOT/'tests/fixtures/printf_buffer_original.manifest.json');cls.case=cls.fixture['cases'][0]
        for call in cls.case['printf_calls']:
            m,_=engine(cls.fixture,call['before'])
            if m.u32(call['before']['registers']['esp']+12)>=3:
                cls.one=dict(cls.case,printf_calls=[call]);break
        else:raise AssertionError('Missing native nonempty buffer write')

    def test_all_histories_provenance_and_complete_native_owner_manifests(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        self.assertEqual(f['printf_buffer_provenance']['observer'],capture.OBSERVER)
        self.assertEqual(f['integer_cpu']['probe'],CPU_PROBE)
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        contexts=f.get('printf_contexts',{})
        for key,context in contexts.items():self.assertEqual(digest_context(context),key)
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0];self.assertEqual(f['gdb_commands'],capture.commands(Path(directory)))
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            for call in c['printf_calls']:
                self.assertEqual(set(call),{'before','after','children'});a,b=(call[p]for p in ('before','after'))
                self.assertEqual(a['registers']['esp']+4,b['registers']['esp'])
                context=contexts[a['printf_context']]if 'printf_context'in a else a
                self.assertLessEqual(set(context['environment']),{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'})
                for child in call['children']:self.assertEqual(set(child),{'kind','before','after'});self.assertEqual(child['before']['esp']+4,child['after']['esp'])
        self.assertEqual(set(f['loader_record_keys']),set(f['loader_records']))
        for key,region in f['loader_records'].items():self.assertEqual(key,record_id(region))

    def test_every_native_memory_register_fp_byte_and_child_register(self):
        f=self.fixture;shard=int(os.environ.get('PYASITIC_PRINTF_SHARD','1'));shards=int(os.environ.get('PYASITIC_PRINTF_SHARDS','1'));report=run(f,shard=shard,shards=shards)
        # The report is produced by this full audit, avoiding a second replay
        # solely to export identical results. Every shard is strict.
        if target:=os.environ.get('PYASITIC_PRINTF_REPORT'):Path(target).write_text(json.dumps(report,indent=2)+'\n')
        self.assertEqual(report['differences'],0);cases=[f['cases'][i]for i in report['case_indices']];calls=[call for c in cases for call in c['printf_calls']]
        self.assertEqual(report['calls_checked'],len(calls));self.assertEqual(report['registers_checked'],17*len(calls));self.assertEqual(report['fp_bytes_checked'],sum(len(unpack_state(f,call['after'])['xstate'])//2 for call in calls))
        children=sum(len(call['children'])for call in calls);self.assertEqual(report['children_checked'],children);self.assertEqual(report['child_registers_checked'],34*children)
        words=[(f['loader_records'][key]['size']+3)//4 for key in f['loader_record_keys']]
        self.assertEqual(report['words_checked'],sum(words[i]for call in calls for i in unpack_state(f,call['after'])['region_ids']))

    def test_later_memory_register_fp_child_and_owner_targets_are_assertions(self):
        f=dict(self.fixture,loader_regions={});c=copy.deepcopy(self.one);call=c['printf_calls'][0]
        for phase in ('before','after'):call[phase]=expand_state(f,call[phase])
        b=call['after'];address=b['registers']['esp']-8;r=next(r for r in b['regions']if r['address']<=address<r['address']+r['size']);raw=bytearray(data(f,r));raw[address-r['address']]^=1;key=hashlib.sha256(raw).hexdigest();f['loader_regions'][key]=raw.hex();r.pop('pages',None);r.pop('printf_page_ids',None);r['sha256']=key
        b['registers']['eax']^=1;b['xstate']='00'+b['xstate'][2:];call['children'][0]['before']['ebx']^=1;call['children'][0]['after']['ecx']^=1
        self.assertEqual(collections.Counter(d['kind']for d in compare(f,c)['differences']),{'printf-memory-word':1,'printf-register':1,'printf-fp-byte':1,'printf-child-register':2})
        b['regions'].pop();self.assertIn('printf-region-owners',[d['kind']for d in compare(f,c)['differences']])

    def test_earlier_source_bytes_and_count_determine_the_copy(self):
        call=self.one['printf_calls'][0];m,storage=engine(self.fixture,call['before']);r=call['before']['registers'];s=r['esp'];buf=m.u32(s+4);src=m.u32(s+8);pointer=m.u32(buf+4)
        m.write(src,b'XYZ');m.put_u32(s+12,3);result=storage.write(r)
        self.assertEqual(m.read(pointer,3),b'XYZ');self.assertEqual(m.u32(buf+4),pointer+3);self.assertEqual((result['eax'],result['edx'],result['ecx']),(pointer+3,src+3,0));self.assertEqual(len(storage.children),1)

    def test_zero_count_or_failed_mode_never_reads_source(self):
        call=self.one['printf_calls'][0];r=call['before']['registers']
        for failed in (False,True):
            m,storage=engine(self.fixture,call['before']);s=r['esp'];buf=m.u32(s+4);src=m.u32(s+8);count=m.u32(s+12);pointer=m.u32(buf+4);mode=m.u32(buf+20)
            if failed:m.put_u32(buf+20,0)
            else:m.put_u32(s+12,0)
            m.forget(src,count);result=storage.write(dict(r,eflags=r['eflags']|0x400))
            self.assertEqual(storage.children,[]);self.assertEqual(m.u32(buf+4),pointer);self.assertEqual(result['eax'],0 if failed else mode);self.assertEqual(result['ecx'],r['ecx']);self.assertEqual(result['edx'],src);self.assertTrue(result['eflags']&0x400)

    def test_missing_earlier_bytes_cannot_use_return_snapshot(self):
        call=self.one['printf_calls'][0];r=call['before']['registers']
        for which in ('source','buffer'):
            m,storage=engine(self.fixture,call['before']);s=r['esp'];buf=m.u32(s+4)
            if which=='source':m.forget(m.u32(s+8),m.u32(s+12))
            else:m.forget(buf+4,4)
            with self.assertRaises(UnknownMemory):storage.write(r)

    def test_exhausted_buffer_requires_its_flush_child(self):
        call=self.one['printf_calls'][0];m,storage=engine(self.fixture,call['before']);r=call['before']['registers'];buf=m.u32(r['esp']+4);m.put_u32(buf+4,m.u32(buf+8))
        with self.assertRaisesRegex(NotImplementedError,'flush-mode'):storage.write(r)

    def test_source_pointer_addition_wraps_at_the_i386_address_boundary(self):
        m=Memory(AddressSpace([dict(start=0x1000,end=0x2000),dict(start=0x3000,end=0x4000),dict(start=0xfffff000,end=0x100000000)]));base=0x10000000;s=0x1800;buf=0x3100;destination=0x3200;source=0xfffffffc
        r=dict(self.one['printf_calls'][0]['before']['registers'],esp=s,eip=base+0x58750)
        for offset,value in ((0,0x8012345),(4,buf),(8,source),(12,4)):m.put_u32(s+offset,value)
        for offset,value in ((0,destination),(4,destination),(8,destination+32),(12,0),(16,0),(20,4)):m.put_u32(buf+offset,value)
        m.write(source,b'WXYZ');storage=PrintfBuffer(m,libc_base=base,shr1_af=self.fixture['integer_cpu']['shr1_af']);result=storage.write(r)
        self.assertEqual(m.read(destination,4),b'WXYZ');self.assertEqual(result['edx'],0);self.assertEqual(m.u32(s+8),source);self.assertEqual(result['eax'],destination+4)

    def test_shards_partition_every_history_without_exemptions(self):
        count=len(self.fixture['cases'])
        for shards in (1,2,8,count):self.assertEqual(sorted(i for shard in range(1,shards+1)for i in selected_indices(count,shard,shards)),list(range(count)))
        for shard,shards in ((0,1),(2,1),(1,0),(True,1),(1,count+1)):
            with self.assertRaises(ValueError):selected_indices(count,shard,shards)

    def test_capture_compacts_incrementally_without_changing_any_snapshot_field(self):
        a=dict(registers={'eax':1},xstate='7f03',maps=[{'address':12}],regions=[dict(address=0x1000,data='4142'),dict(address=0x1004,data='4344')])
        b=dict(registers={'eax':2},xstate='7f03',regions=[dict(address=0x1000,data='415a'),dict(address=0x1004,data='4344')]);original=copy.deepcopy([a,b])
        case=dict(label='projection',cache_mode='cold',printf_calls=[dict(before=a,after=b,children=[])]);projection=capture.PrintfProjection();self.assertIs(projection.case(case),case);f=projection.metadata()
        self.assertEqual(f['printf_projection']['states_checked'],2)
        for state,expected in zip((a,b),original):
            expanded=expand_state(f,state);regions=expanded.pop('regions');self.assertEqual(expanded,{k:v for k,v in expected.items()if k!='regions'})
            self.assertEqual([dict(address=r['address'],data=data(f,r).hex())for r in regions],expected['regions'])


if __name__=='__main__':unittest.main()
