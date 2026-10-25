"""Native printf FILE setup/completion, full owners and allocation state."""
import collections,copy,hashlib,json,os,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_printf_file_original as capture
from audit_printf_file_original import compare,engine,run,selected_indices
from printf_fixture import data,expand_state,unpack_state,digest_context
from printf_archive import read_fixture
from reasitic.memory import UnknownMemory


class PrintfFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=read_fixture(ROOT/'tests/fixtures/printf_file_original.manifest.json');cls.case=cls.fixture['cases'][0]
        cls.staged=next(call for call in cls.case['printf_calls']if any(c['kind']=='malloc'for c in call['children']))
        cls.one=dict(cls.case,printf_calls=[cls.staged])

    def test_all_unchanged_jobs_and_complete_native_provenance(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(jobs),67);self.assertEqual(len(f['cases']),134)
        self.assertEqual(f['printf_file_provenance']['observer'],capture.OBSERVER)
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0];self.assertEqual(f['gdb_commands'],capture.commands(Path(directory)))
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        self.assertEqual(f['original_sha256'],'72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f')
        self.assertEqual(f['legacy_sha256'],'bca97b602b1eec9f0b591bec0fa4dc5f84f1382636cc8f10094f1da8a3c77d34')
        for key,context in f['printf_contexts'].items():self.assertEqual(key,digest_context(context))
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            for call in c['printf_calls']:
                self.assertEqual(set(call),{'kind','before','after','children'});self.assertIn(call['kind'],('init','done'))
                a,b=(unpack_state(f,call[p])for p in ('before','after'))
                self.assertEqual(a['registers']['esp']+4,b['registers']['esp'])
                self.assertLessEqual(set(a['environment']),{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'})
                for child in call['children']:
                    self.assertEqual(set(child),{'kind','before','after'});self.assertEqual(child['before']['esp']+4,child['after']['esp'])

    def test_every_native_memory_register_fp_heap_and_child_boundary(self):
        f=self.fixture;report=run(f,shard=int(os.environ.get('PYASITIC_PRINTF_FILE_SHARD','1')),shards=int(os.environ.get('PYASITIC_PRINTF_FILE_SHARDS','1')))
        if target:=os.environ.get('PYASITIC_PRINTF_FILE_REPORT'):Path(target).write_text(json.dumps(report,indent=2)+'\n')
        self.assertEqual(report['differences'],0)
        calls=[call for i in report['case_indices']for call in f['cases'][i]['printf_calls']]
        self.assertEqual(report['calls_checked'],len(calls));self.assertEqual(report['registers_checked'],17*len(calls))
        self.assertEqual(report['fp_bytes_checked'],sum(len(unpack_state(f,c['after'])['xstate'])//2 for c in calls))
        children=sum(len(c['children'])for c in calls);self.assertEqual(report['children_checked'],children);self.assertEqual(report['child_registers_checked'],34*children)
        words=[(f['loader_records'][key]['size']+3)//4 for key in f['loader_record_keys']]
        self.assertEqual(report['words_checked'],sum(words[i]for call in calls for i in unpack_state(f,call['after'])['region_ids']))

    def test_later_memory_heap_register_fp_and_child_targets_are_assertions(self):
        f=dict(self.fixture,loader_regions={});c=copy.deepcopy(self.one);call=c['printf_calls'][0]
        for phase in ('before','after'):call[phase]=copy.deepcopy(expand_state(f,call[phase]))
        b=call['after'];address=b['registers']['esp']-8;region=next(r for r in b['regions']if r['address']<=address<r['address']+r['size'])
        raw=bytearray(data(f,region));raw[address-region['address']]^=1;key=hashlib.sha256(raw).hexdigest();f['loader_regions'][key]=raw.hex()
        region.pop('pages',None);region.pop('printf_page_ids',None);region['sha256']=key
        b['registers']['eax']^=1;b['xstate']='00'+b['xstate'][2:];b['heap']['top']+=16
        call['children'][0]['before']['ebx']^=1;call['children'][0]['after']['ecx']^=1
        counts=collections.Counter(d['kind']for d in compare(f,c)['differences'])
        self.assertEqual(counts,{'printf-memory-word':1,'printf-register':1,'printf-fp-byte':1,'state':1,'printf-child-register':2})
        b['regions'].pop();self.assertIn('printf-region-owners',[d['kind']for d in compare(f,c)['differences']])

    def test_earlier_staged_bytes_determine_allocated_file_output(self):
        a=expand_state(self.fixture,self.staged['before']);m,storage=engine(self.fixture,a);r=a['registers'];buf=m.u32(r['esp']+4);file=m.u32(buf+24)
        source=buf+28;count=m.u32(buf+4)-source;before=m.read(source,count);m.write(source,b'XYZ');result=storage.done(r)
        pointer=m.u32(file+28);self.assertEqual(m.read(pointer,count),b'XYZ'+before[3:]);self.assertEqual(m.u32(file+20),pointer+count)
        self.assertEqual(result['eax'],count);self.assertEqual(m.u32(buf+4),pointer+count)
        self.assertEqual([c['kind']for c in storage.children],[c['kind']for c in self.staged['children']])

    def test_every_additional_heap_target_remains_required(self):
        c=copy.deepcopy(self.one);call=c['printf_calls'][0]
        call['after']=copy.deepcopy(expand_state(self.fixture,call['after']));target=call['after']['heap']
        target['parameters']['top_pad']^=16;target['flags']^=1;target['tcache_counts'][0]+=1
        raw=bytearray.fromhex(target['arena_bytes']);raw[0]^=1;target['arena_bytes']=raw.hex()
        target['maps'][0]['permissions']='---p';target['event_count']+=1;target['errors'].append(dict(section='tcache.0',reason='injected'))
        counts=collections.Counter(d['kind']for d in compare(self.fixture,c)['differences'])
        self.assertEqual(counts['printf-heap-field'],3);self.assertEqual(counts['printf-arena-image'],1)
        self.assertEqual(counts['printf-mappings'],1);self.assertEqual(counts['printf-observer-event-count'],1);self.assertEqual(counts['printf-heap-errors'],1)

    def test_missing_earlier_input_never_uses_later_snapshot(self):
        a=expand_state(self.fixture,self.staged['before'])
        for missing in ('source','file','canary'):
            m,storage=engine(self.fixture,a);r=a['registers'];buf=m.u32(r['esp']+4)
            address=buf+28 if missing=='source'else m.u32(buf+24)+28 if missing=='file'else storage.tls+20
            m.forget(address,4)
            with self.subTest(missing=missing),self.assertRaises(UnknownMemory):storage.done(r)

    def test_init_writes_uninitialized_buffer_and_selects_earlier_file_space(self):
        call=next(c for c in self.case['printf_calls']if c['kind']=='init');a=expand_state(self.fixture,call['before']);m,storage=engine(self.fixture,a);r=a['registers'];buf=m.u32(r['esp']+4);file=m.u32(r['esp']+8)
        m.forget(buf,156);start=m.u32(file+20);end=m.u32(file+24);storage.init(r)
        pointer=start if start<end else buf+28;stop=end if start<end else buf+156
        self.assertEqual([m.u32(buf+i)for i in (0,4,8,12,16,20,24)],[pointer,pointer,stop,0,0,4,file])

    def test_failed_mode_does_not_read_or_flush_file(self):
        a=expand_state(self.fixture,self.staged['before']);m,storage=engine(self.fixture,a);r=a['registers'];buf=m.u32(r['esp']+4);m.put_u32(buf+20,0);m.forget(buf+24,4)
        result=storage.done(r);self.assertEqual(result['eax'],0xffffffff);self.assertEqual(storage.children,[])

    def test_count_completion_reports_signed_overflow_to_actual_errno_tls(self):
        a=expand_state(self.fixture,self.staged['before'])
        for count,expected in ((0,0),(0x7fffffff,0x7fffffff),(0x80000000,0xffffffff),(0x100000000,0xffffffff)):
            m,storage=engine(self.fixture,a);r=dict(a['registers'],eip=storage.libc+0x58190);buf=m.u32(r['esp']+4);pointer=m.u32(buf+4)
            m.put_u32(buf,pointer);m.put_u32(buf+12,count);m.put_u32(buf+16,count>>32)
            errno=(m.u32(storage.tls)+m.u32(storage.got+0xa0))&0xffffffff;m.put_u32(errno,0)
            result=storage.buffer_done(r);self.assertEqual(result['eax'],expected)
            self.assertEqual(m.u32(errno),75 if count>0x7fffffff else 0)

    def test_top_split_rejects_conflicting_earlier_metadata(self):
        a=expand_state(self.fixture,self.staged['before'])
        for field in ('top','fd'):
            m,storage=engine(self.fixture,a);r=a['registers'];buf=m.u32(r['esp']+4);file=m.u32(buf+24)
            if field=='top':m.put_u32(storage.heap.arena_address+56,storage.heap.top+16)
            else:storage.io.profile=dict(storage.io.profile,fd=99)
            with self.subTest(field=field),self.assertRaises(ValueError):storage.done(r)

    def test_shards_cover_every_history_once(self):
        count=len(self.fixture['cases'])
        for shards in (1,2,8,count):self.assertEqual(sorted(i for shard in range(1,shards+1)for i in selected_indices(count,shard,shards)),list(range(count)))
        for shard,shards in ((0,1),(2,1),(1,0),(True,1),(1,count+1)):
            with self.assertRaises(ValueError):selected_indices(count,shard,shards)


if __name__=='__main__':unittest.main()
