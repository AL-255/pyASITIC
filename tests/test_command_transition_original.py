"""Capture integrity, parser stores, and independence of later command outputs.

The mandatory all-case audit additionally compares every byte, including the
unresolved reused-stack words in the rectangular native abort. These tests do
not replace that strict audit with an expected-difference allowance.
"""
import ast,collections,copy,gzip,hashlib,json,os,re,struct,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_command_transition_original as capture
from capture_prelude_storage_extended_original import jobs as extra_jobs
from audit_command_transition_original import compare
from reasitic.command_storage import Characters,CommandStorage,ScanHistory
from reasitic.command_catalog import CATALOG
from reasitic.port_header_storage import NativePortStack,calendar
from reasitic.memory import Memory
from reasitic.heap import AddressSpace


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class CommandTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=load('command_transition_original.json.gz');cls.extended=load('command_transition_extended_original.json.gz')

    def test_all_jobs_parent_hashes_and_full_native_boundaries_retained(self):
        cases=0;faults=[]
        jobs=list(capture.node.console.driver.cache.libio.prelude.geometry.arena.lifetime.jobs())
        for fixture,work,parent_name in ((self.fixture,jobs,'node_history_original.json.gz'),(self.extended,list(extra_jobs()),'node_history_extended_original.json.gz')):
            self.assertEqual(len(fixture['cases']),2*len(work));self.assertEqual(fixture['allocator_provenance']['observer'],capture.OBSERVER)
            self.assertEqual(fixture['driver_history_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures'/parent_name).read_bytes()).hexdigest())
            for name,digest in fixture['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
            directory=fixture['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
            self.assertEqual(fixture['gdb_commands'],capture.commands(Path(directory)))
            previous=load(parent_name)
            for entry,old,job in zip(fixture['cases'],previous['cases'],(j for j in work for _ in range(2))):
                cases+=1
                for key in ('label','request','script','stdin','variant'):self.assertEqual(entry[key],job[key])
                self.assertEqual(entry['cache_mode'],old['cache_mode']);self.assertEqual(entry['post_driver'],old['post_driver'])
                case=capture.expand_case(fixture,entry)
                if case['signal']:faults.append((entry['label'],entry['cache_mode'],case['signal']))
                for state in case['transition_states']:
                    self.assertEqual([(r['address'],len(r['data'])//2)for r in state['memory_regions']],[(m['start'],m['end']-m['start'])for m in state['maps']if m['path']=='[heap]'])
                    self.assertEqual([len(r['data'])//2 for r in state['component_regions']],[4460,120])
                for buffer in case['transition_buffers']:
                    event=case['transition_events'][buffer['event_index']]
                    self.assertEqual(event['kind'],'free');self.assertEqual(event['address'],buffer['address']);self.assertEqual(len(buffer['data']),2*buffer['size'])
            for bank in ('driver_heap_pages','cache_file_pages','storage_pages','storage_blobs'):
                for digest,data in fixture[bank].items():self.assertEqual(hashlib.sha256(bytes.fromhex(data)).hexdigest(),digest)
        self.assertEqual(cases,134)
        self.assertIn(('prelude/fft/16/8','cold',6),faults)
        self.assertIn(('square/64/contacts','cold',11),faults)

    def test_fixed_parser_records_match_native_port_header_entry(self):
        # Earlier pre-parse storage is the isolated parser's input. Later
        # header-entry records are assertions only, never source values.
        for entry in self.extended['cases']:
            if entry['transition_end']is None:continue
            a,b=entry['transition_points'];self.assertEqual((a['kind'],b['kind']),('parse','header'))
            region=a['regions'][0];address=region['address'];space=AddressSpace([dict(start=address&~4095,end=(address+4460+4095)&~4095,permissions='rw-p',path='[stack]')])
            memory=Memory(space);memory.write(address,bytes.fromhex(region['data']))
            pointer=memory.u32(address+516);name=memory.read(address+260,256).split(b'\0',1)[0];warnings=[]
            parser=CommandStorage(memory,Characters(entry['transition_inputs']['character_tables']),lambda text:pointer if text==name else None,warnings.append)
            self.assertEqual(parser.parse(address+4160,address,[ScanHistory(0.,0,0)for _ in range(15)]),528)
            self.assertEqual(warnings,[]);self.assertEqual(memory.read(address,4460).hex(),b['regions'][0]['data'])

    def test_catalog_is_the_complete_reference_definition(self):
        source=(ROOT/'tests/fixtures/command_catalog_reference.inc').read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(),'ff9842bc5adeaf13a029c933ce43123148e7cda4d2b1b44f9a2daf481d1eb477')
        rows=ast.literal_eval('['+source.decode().replace('{','[').replace('}',']')+']')
        expected=tuple((i,tuple(aliases),low,high,usage,tuple(types))for i,aliases,low,high,usage,types in rows if i!=-2)
        self.assertEqual(CATALOG,expected);self.assertEqual(len(CATALOG),117)

    def test_fresh_plain_faults_and_changed_outcomes_remain_explicit(self):
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in self.fixture['cases']),{0:123,-6:6,-11:1})
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in self.extended['cases']),{0:3,-6:1})
        old=load('node_history_original.json.gz')
        changed=[(a['label'],a['cache_mode'],a['plain']['returncode'],b['plain']['returncode'])for a,b in zip(old['cases'],self.fixture['cases'])if a['plain']['returncode']!=b['plain']['returncode']]
        self.assertEqual(changed,[('square/1/coarse','cold',-6,0),('square/1/coarse','warm',0,-6),('pilot-width3/1/contacts','cold',0,-6),('pilot-width3/1/contacts','warm',0,-6)])
        for fixture in (self.fixture,self.extended):
            for entry in fixture['cases']:
                if entry['plain']['returncode']==-6:self.assertEqual(entry['plain']['stderr'],'malloc(): unaligned tcache chunk detected\n'if fixture is self.fixture else'double free or corruption (!prev)\n')

    def test_failed_scan_requires_earlier_caller_value(self):
        memory=Memory(AddressSpace([dict(start=0x1000,end=0x2000)]));memory.zero(0x1000,4096)
        memory.write(0x1000,b'nonsense\0');warnings=[]
        parser=CommandStorage(memory,Characters(self.extended['cases'][0]['transition_inputs']['character_tables']),lambda name:None,warnings.append)
        with self.assertRaisesRegex(NotImplementedError,'earlier caller number slot'):
            parser.parse_argument(0x1000,5,ScanHistory(None,None,None))
        self.assertTrue(parser.parse_argument(0x1000,5,ScanHistory(2.,None,None)))
        self.assertEqual(memory.read(0x1100,4),struct.pack('<f',2e9));self.assertEqual(warnings,[])

    def test_stack_capture_environment_is_explicit_and_cannot_inherit_credentials(self):
        factory=capture.node.console.driver.cache.libio.prelude.geometry.arena.lifetime.native_environment
        with patch.dict(os.environ,{'PRIVATE_TOKEN':'must-not-be-inherited'}):environment=factory('/native/libraries')
        self.assertEqual(environment,dict(PATH=os.defpath,HOME='/tmp',LANG='C',LC_ALL='C',LD_LIBRARY_PATH='/native/libraries',TERM='dumb',INPUTRC='/dev/null'))
        allowed={'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'}
        for fixture in (self.fixture,self.extended):
            for entry in fixture['cases']:
                inputs=entry['transition_inputs'];self.assertLessEqual(set(inputs['environment']),allowed)
                for key,value in fixture['environment_overrides'].items():self.assertEqual(inputs['environment'][key],value)
                stack=max(inputs['initial_regions'],key=lambda r:len(r['data']))
                contents=bytes.fromhex(stack['data'])
                # Check the actual retained bytes, rather than only a metadata
                # claim. An unexpected credential-shaped variable is a failure.
                keys=[m.group(1)for part in contents.split(b'\0')if(m:=re.match(rb'^([A-Za-z_][A-Za-z0-9_]*)=',part))]
                self.assertFalse([key for key in keys if re.search(rb'KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL',key,re.I)])

    def test_timestamp_follows_source_filename_pushes_and_native_writers(self):
        fixture=json.loads((ROOT/'tests/fixtures/port_timestamp_writers_original.json').read_text())
        self.assertEqual(fixture['original_sha256'],'72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f')
        for entry,identity,pc in zip(fixture['cases'],(528,524),(0x80b2219,0x804ab94)):
            frame=entry['registers']['ebp'];source=entry['workspace_address']+8*260
            space=AddressSpace([dict(start=(frame-4096)&~4095,end=(frame+4096)&~4095,permissions='rw-p',path='[stack]')]);memory=Memory(space)
            stack=NativePortStack(memory,frame);stack.filename_copy(source,123456,5)
            address,value=stack.timestamp(identity);last=entry['watch'][-1]
            self.assertEqual(last['pc'],pc);self.assertEqual((address,value&0xffffffff),(last['address'],last['value']))
            self.assertEqual(entry['calendar'][0]['address'],address);self.assertEqual(entry['calendar'][0]['data'],struct.pack('<i',value).hex())

    def test_calendar_uses_earlier_timezone_file(self):
        for entry in self.extended['cases']:
            for call in entry['transition_calendar']:
                stamp=struct.unpack('<i',bytes.fromhex(call['data']))[0]
                self.assertEqual(calendar(stamp,bytes.fromhex(entry['transition_inputs']['timezone']['tzfile'])).hex(),call['text'])

    def test_later_text_calendar_and_boundary_bytes_are_comparisons_only(self):
        entry=self.extended['cases'][1]
        self.assertEqual(compare(self.extended,entry)['differences'],[])
        changed=copy.deepcopy(entry);changed['transition_end']['files'][0]['data']='00'+changed['transition_end']['files'][0]['data'][2:]
        changed['transition_calendar'][0]['text']='00'+changed['transition_calendar'][0]['text'][2:]
        region=changed['transition_points'][0]['regions'][0];region['data']='00'+region['data'][2:]
        result=compare(self.extended,changed)
        self.assertEqual({d['kind']for d in result['differences']},{'transition-file','transition-calendar','transition-point-word'})
        self.assertEqual(result['events_checked'],5);self.assertEqual(result['files_checked'],1)


if __name__=='__main__':unittest.main()
