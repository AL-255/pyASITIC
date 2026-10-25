"""Real printf/flush on the continuously produced ASITIC process memory."""
import collections,copy,gzip,hashlib,json,os,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_printf_transition_original as capture
from audit_printf_transition_original import compare,run
from audit_loader_lookup_original import data
from reasitic.printf_entry_storage import PrintfEntryStorage
from reasitic.libio_storage import FileStorage


def load(path):return json.loads(gzip.decompress(Path(path).read_bytes()))


class PrintfTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=load(os.environ.get('PYASITIC_PRINTF_TRANSITION_FIXTURE',ROOT/'tests/fixtures/printf_transition_original.json.gz'));cls.case=next(c for c in cls.fixture['cases']if c['label']=='prelude/fft/16/8'and c['cache_mode']=='cold')

    def test_all_jobs_earlier_controls_and_complete_later_owners(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        self.assertEqual(collections.Counter(c['signal']for c in f['cases']),{0:132,11:1,6:1});self.assertEqual(sum(len(c['printf_transition_calls'])for c in f['cases']),3)
        p=f['printf_transition_provenance'];self.assertEqual(p['observer'],capture.OBSERVER);self.assertIsNone(p['pilot_label']);self.assertEqual(p['parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures/flush_transition_original.json.gz').read_bytes()).hexdigest())
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            for field in('allocator_states','post_states','transition_states'):
                for s in c[field]:
                    targets=s['cache_node_targets'];self.assertEqual(len({r['address']for r in targets}),len(targets))
                    outside={p for chain in s['tcache']for p in chain if not any(r['address']<=p and p+8<=r['address']+r['size']for r in s['memory_regions'])}
                    self.assertEqual({r['address']for r in targets},outside)
                    for r in targets:self.assertEqual(len(bytes.fromhex(r['data'])),8)
            stdio=c['transition_inputs']['stdio_context'];self.assertTrue(stdio['printf_abi']);self.assertTrue(stdio['flush_abi']);self.assertEqual(len(stdio['regions']),44);self.assertEqual(sum(r['size']for r in stdio['regions']),254478)
            owners=[(r['address'],r['size'])for r in stdio['regions']]
            for later in c['transition_points']+c['transition_states']:
                regions=later.get('regions',later.get('component_regions'));self.assertEqual([(r['address'],r['size'])for r in regions[2:]],owners)
                for r in regions:self.assertEqual(len(data(f,r)),r['size'])
            self.assertNotIn('printf_transition_calls',c['transition_inputs']);self.assertNotIn('xstate',stdio)

    def test_every_continuing_target_stays_required(self):
        f=self.fixture;report=run(f,shard=int(os.environ.get('PYASITIC_PRINTF_TRANSITION_SHARD','1')),shards=int(os.environ.get('PYASITIC_PRINTF_TRANSITION_SHARDS','1')))
        if target:=os.environ.get('PYASITIC_PRINTF_TRANSITION_REPORT'):Path(target).write_text(json.dumps(report,indent=2)+'\n')
        cases=[f['cases'][i]for i in report['case_indices']];calls=sum(len(c['printf_transition_calls'])for c in cases)
        self.assertEqual(report['printf_calls_checked'],calls);self.assertEqual(report['printf_registers_checked'],34*calls)
        self.assertEqual(report['component_words_checked'],sum(r['size']//4 for c in cases for s in c['transition_states']for r in s['component_regions']))
        self.assertEqual(report['point_words_checked'],sum(r['size']//4 for c in cases for p in c['transition_points']for r in p['regions']))
        self.assertEqual(report['point_bytes_checked'],sum(r['size']for c in cases for p in c['transition_points']for r in p['regions']))
        self.assertEqual(report['component_bytes_checked'],sum(r['size']for c in cases for s in c['transition_states']for r in s['component_regions']))
        self.assertEqual(report['differences'],0,'Every old/new owner, printf register and native outcome remains required')

    def test_generated_printf_runs_on_the_same_memory_and_preserves_opaque_fp(self):
        original=PrintfEntryStorage.entry;seen=[];memories=[];heaps=[]
        def observe(storage,registers):
            before=dict(registers);memories.append(storage.m);heaps.append(storage.heap);self.assertIsNone(storage.xstate);self.assertTrue(storage.preserve_fp);result=original(storage,registers);self.assertIsNone(storage.xstate);seen.append(dict(kind='printf'if before['eip']==storage.libc+0x57db0 else'fprintf',before=before,after=dict(result)));return result
        with patch.object(PrintfEntryStorage,'entry',observe):report,heap,_,memory=compare(self.fixture,self.case,return_state=True)
        self.assertEqual(seen,self.case['printf_transition_calls']);self.assertEqual(len(seen),3);self.assertTrue(all(m is memory for m in memories));self.assertTrue(all(h is heap for h in heaps));self.assertFalse(any(d['kind']=='transition-runtime'for d in report['differences']))

    def test_missing_earlier_table_does_not_use_later_region_copies(self):
        c=copy.deepcopy(self.case);ctx=c['transition_inputs']['loader_context'];section=next(s for e in c['transition_inputs']['stdio_context']['printf_elf']if e['path'].endswith('/libc.so.6')for s in e['sections']if s['name']=='.rodata')
        ctx['regions']=[r for r in ctx['regions']if r['address']!=section['address']]
        report=compare(self.fixture,c);self.assertTrue(any(d['kind']=='transition-runtime'and'Uninitialized guest memory'in d['reason']for d in report['differences']))

    def test_later_region_and_printf_return_are_assertions(self):
        base=compare(self.fixture,self.case);c=copy.deepcopy(self.case);c['printf_transition_calls'][0]['after']['eax']^=1
        r=next(r for r in c['transition_points'][0]['regions'][35:]if r['size']>4096);address=r['address'];raw=bytearray(data(self.fixture,r));raw[0]^=1;r.clear();r.update(address=address,data=raw.hex())
        changed=compare(self.fixture,c);delta=collections.Counter(d['kind']for d in changed['differences'])-collections.Counter(d['kind']for d in base['differences'])
        self.assertEqual(delta['transition-printf-register'],1);self.assertEqual(delta['transition-point-word'],1)

    def test_changed_earlier_prompt_reaches_actual_printf_output(self):
        c=copy.deepcopy(self.case);f=dict(self.fixture,loader_regions=dict(self.fixture['loader_regions']));raw=b'NEW\0';key=hashlib.sha256(raw).hexdigest();f['loader_regions'][key]=raw.hex();c['transition_inputs']['loader_context']['regions'].append(dict(address=0x80b4821,size=len(raw),sha256=key));seen=[];original=PrintfEntryStorage.entry
        def observe(storage,registers):
            result=original(storage,registers)
            if registers['eip']==storage.libc+0x57db0:
                file=storage.m.u32(0x80d7d68);end=storage.m.u32(file+20);seen.append((result['eax'],storage.m.read(end-4,4)))
            return result
        with patch.object(PrintfEntryStorage,'entry',observe):report=compare(f,c)
        self.assertEqual(seen,[(4,b'\nNEW')]);self.assertFalse(any(d['kind']=='transition-runtime'for d in report['differences']));self.assertTrue(any(d['kind']=='transition-printf-register'for d in report['differences']))

    def test_absent_cache_file_produces_errno_in_shared_tls(self):
        events=[];original=FileStorage.failed_open
        def observe(storage,address,**kwargs):
            before=storage.memory.u32(storage.errno_address);original(storage,address,**kwargs);events.append((before,storage.memory.u32(storage.errno_address),kwargs))
        with patch.object(FileStorage,'failed_open',observe):report=compare(self.fixture,self.case)
        self.assertEqual(events,[(0,2,{'error_number':2})]);self.assertFalse(any(d['kind']=='transition-runtime'for d in report['differences']))

    def test_complete_region_codec_retains_bytes_and_detects_corruption(self):
        f=dict(loader_regions={},cases=[dict(transition_points=[dict(regions=[dict(address=16,data='0001ff02')])],transition_states=[])])
        capture.project_regions(f);r=f['cases'][0]['transition_points'][0]['regions'][0];self.assertEqual(data(f,r),b'\0\1\xff\2');self.assertEqual(f['printf_transition_projection']['regions_checked'],1)
        f['loader_regions'][r['sha256']]='00000000'
        with self.assertRaises((ValueError,AssertionError)):data(f,r)

    def test_external_cache_targets_are_read_only_assertions(self):
        from audit_allocator_original import state_differences
        from capture_command_transition_original import expand_case
        _,heap,_,memory=compare(self.fixture,self.case,return_state=True)
        state=copy.deepcopy(expand_case(self.fixture,self.case)['transition_states'][-1])
        section=next(s for e in self.case['transition_inputs']['stdio_context']['printf_elf']if e['path'].endswith('/libc.so.6')for s in e['sections']if s['name']=='.rodata')
        address=section['address'];region=next(r for r in state['component_regions']if r['address']==address);native=bytes.fromhex(region['data'])[:8]
        state['cache_node_targets']=[dict(address=address,data=native.hex())]
        before=memory.read(address,8);baseline=state_differences(heap,state,memory=memory)
        self.assertFalse(any(d['kind']=='external-cache-node'for d in baseline))
        state['cache_node_targets'][0]['data']=(bytes([native[0]^1])+native[1:]).hex()
        changed=state_differences(heap,state,memory=memory)
        self.assertEqual(collections.Counter(d['kind']for d in changed)-collections.Counter(d['kind']for d in baseline),{'external-cache-node':1})
        self.assertEqual(memory.read(address,8),before)
        self.assertTrue(any(d['kind']=='external-cache-node'and d['actual']is None for d in state_differences(heap,state)))


if __name__=='__main__':unittest.main()
