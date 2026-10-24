"""Earlier stream inputs, independent later traces, and strict full-heap stores."""
import copy,gzip,hashlib,json,struct,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_console_storage_original as capture
from capture_prelude_storage_extended_original import jobs as extra_jobs
from capture_driver_history_original import expand_case
from audit_console_storage_original import compare
from reasitic.console_storage import ConsoleStorage


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class ConsoleStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=load('console_storage_original.json.gz');cls.extended=load('console_storage_extended_original.json.gz')

    def test_every_unchanged_history_and_outcome_retained(self):
        for fixture,jobs,parent in ((self.fixture,list(capture.driver.cache.libio.prelude.geometry.arena.lifetime.jobs()),'driver_history_original.json.gz'),(self.extended,list(extra_jobs()),'driver_history_extended_original.json.gz')):
            self.assertEqual(len(fixture['cases']),2*len(jobs))
            self.assertEqual(fixture['allocator_provenance']['observer'],capture.OBSERVER)
            self.assertEqual(fixture['driver_history_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures'/parent).read_bytes()).hexdigest())
            for name,digest in fixture['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
            directory=fixture['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
            self.assertEqual(fixture['gdb_commands'],capture.commands(Path(directory)))
            previous=load(parent)
            for case,old,job in zip(fixture['cases'],previous['cases'],(job for job in jobs for _ in range(2))):
                for key in ('label','request','script','stdin','variant'):self.assertEqual(case[key],job[key])
                for key in ('label','cache_mode','signal'):self.assertEqual(case[key],old[key])
                self.assertEqual(len(case['events']),len(old['events']))
                self.assertEqual(len(case['workspace_storage']),len(old['workspace_storage']))
                self.assertEqual([s['label']for s in case['allocator_states']],[s['label']for s in old['allocator_states']])
                inputs=case['console_inputs'];self.assertFalse(inputs['timing']);self.assertFalse(inputs['matrix_dump'])
                earlier=expand_case(fixture,case)['setup_context']['memory_regions']
                for name,stream in inputs['streams'].items():
                    if stream is None:continue
                    address=stream['address'];data=bytes.fromhex(stream['data']);self.assertEqual(len(data),36)
                    for region in earlier:
                        start=region['address'];raw=bytes.fromhex(region['data'])
                        if start<=address<start+len(raw):self.assertEqual(data,raw[address-start:address-start+36]);break
                    else:self.assertEqual(name,'stdout')
                self.assertGreater(len(case['console_calls']),0)
            for bank in ('driver_heap_pages','cache_file_pages','storage_pages','storage_blobs'):
                for digest,data in fixture[bank].items():self.assertEqual(hashlib.sha256(bytes.fromhex(data)).hexdigest(),digest)
        self.assertEqual(len(self.fixture['cases']),130);self.assertEqual(len(self.extended['cases']),4)

    def test_fresh_plain_allocator_outcomes_remain_explicit_and_old_failures_retained(self):
        # Plain runs have address randomization; GDB disables it. The damaged
        # tcache paths can abort at later cleanup in one plain process and not
        # another. Keep both entire independent captures and the old required
        # driver gate; do not replace its failures with this fresh experiment.
        from collections import Counter
        old=load('driver_history_original.json.gz')
        self.assertEqual(Counter(c['plain']['returncode']for c in old['cases']),{0:123,-6:6,-11:1})
        self.assertEqual(Counter(c['plain']['returncode']for c in self.fixture['cases']),{0:125,-6:4,-11:1})
        changed=[]
        for before,after in zip(old['cases'],self.fixture['cases']):
            if before['plain']['returncode']==after['plain']['returncode']:continue
            changed.append((before['label'],before['cache_mode'],before['plain']['returncode'],after['plain']['returncode']))
            failed=before if before['plain']['returncode']==-6 else after
            self.assertEqual(failed['plain']['stderr'],'malloc(): unaligned tcache chunk detected\n')
            self.assertEqual(before['signal'],after['signal'])
        self.assertEqual(changed,[('square/1/coarse','cold',-6,0),('square/1/coarse','warm',-6,0),('pilot-width3/1/coarse','warm',-6,0),('pilot-width3/1/contacts','cold',-6,0),('pilot-boundary/1/coarse','cold',0,-6),('pilot-boundary/1/coarse','warm',0,-6)])
        old_extra=load('driver_history_extended_original.json.gz')
        self.assertEqual([c['plain']['returncode']for c in self.extended['cases']],[c['plain']['returncode']for c in old_extra['cases']])

    def test_all_small_complete_heaps_and_message_positions_exact(self):
        reports=[compare(self.extended,entry)for entry in self.extended['cases']]
        self.assertEqual([r['differences']for r in reports],[[]]*4)
        self.assertEqual(sum(r['console_calls_checked']for r in reports),106)
        self.assertEqual(sum(r['heap_words_checked']for r in reports),139264)
        self.assertEqual(sum(r['unknown_heap_bytes']for r in reports),0)

    def test_suppressed_source_emitter_leaves_real_heap_differences(self):
        entry=self.extended['cases'][0]
        with patch.object(ConsoleStorage,'_write',return_value=None):result=compare(self.extended,entry)
        self.assertGreater(len(result['differences']),0)
        self.assertEqual({r['kind']for r in result['differences']},{'heap-word'})

    def test_later_message_text_does_not_initialize_runtime(self):
        entry=copy.deepcopy(self.extended['cases'][1]);entry['console_calls'][0]['text']=b'future text must not be replayed'.hex()
        result=compare(self.extended,entry)
        self.assertEqual([d['kind']for d in result['differences']],['console-call'])
        self.assertEqual(result['differences'][0]['actual']['text'],b'Performing Analysis at 0.25 GHz'.hex())

    def test_duplicate_earlier_prefix_cannot_repair_conflicting_heap_bytes(self):
        entry=copy.deepcopy(self.extended['cases'][1]);stream=entry['console_inputs']['streams']['log']
        data=bytearray.fromhex(stream['data']);data[20]^=1;stream['data']=data.hex()
        with self.assertRaisesRegex(ValueError,'Conflicting earlier console FILE bytes'):compare(self.extended,entry)

    def test_earlier_buffer_tail_is_not_replaced_by_later_observation(self):
        entry=copy.deepcopy(self.extended['cases'][1]);stream=entry['console_inputs']['streams']['stdout']
        address=struct.unpack('<9I',bytes.fromhex(stream['data']))[7]+512
        region=next(r for r in entry['setup_context']['memory_regions']if r['address']<=address<r['address']+r['size'])
        page,offset=divmod(address-region['address'],4096);key=region['pages'][page]
        fixture=dict(self.extended,storage_pages=dict(self.extended['storage_pages']))
        data=bytearray.fromhex(fixture['storage_pages'][key]);data[offset]^=1
        changed=hashlib.sha256(data).hexdigest();fixture['storage_pages'][changed]=data.hex();region['pages'][page]=changed
        raw=b''.join(bytes.fromhex(fixture['storage_pages'][p])for p in region['pages']);region['sha256']=hashlib.sha256(raw).hexdigest()
        result=compare(fixture,entry)
        self.assertEqual({d['kind']for d in result['differences']},{'heap-word'})
        self.assertEqual({d['address']for d in result['differences']},{address})


if __name__=='__main__':unittest.main()
