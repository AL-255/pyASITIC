"""All native caller/PUSH targets and source-driven semantic frame events."""
import collections,copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_parser_callers_original as capture
from audit_parser_callers_original import compare,run
from audit_loader_lookup_original import data,memory_for
from reasitic.parser_callers import ParserCallers,parser_to_tokenizer,tokenizer_return_to_catalog,catalog_to_comparison,comparison_argument,COMPARISON_PCS
from reasitic.command_storage import Characters,CommandStorage,ScanHistory,string
from reasitic.command_catalog import CATALOG


class ParserCallersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/parser_callers_original.json.gz').read_bytes()));cls.case=next(c for c in cls.fixture['cases']if c['dispatch_calls']);cls.call=cls.case['dispatch_calls'][0]

    def point(self,name):return capture.expand_point(self.fixture,self.call[name])

    def test_all_jobs_provenance_all_alias_sites_and_complete_owners(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        p=f['parser_callers_provenance'];self.assertEqual(p['observer'],capture.OBSERVER);directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0];self.assertEqual(f['gdb_commands'],capture.commands(Path(directory)))
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        self.assertEqual(collections.Counter(c['signal']for c in f['cases']),{0:132,11:1,6:1});self.assertEqual(collections.Counter(c['plain']['returncode']for c in f['cases']),{0:128,-6:5,-11:1})
        points=owners=total=0;records={}
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            for call in c['dispatch_calls']:
                layout=[(r['address'],r['size'])for r in capture.expand_point(f,call['entry'])['regions']]
                for raw in capture.points(call):
                    point=capture.expand_point(f,raw);self.assertEqual([(r['address'],r['size'])for r in point['regions']],layout);points+=1;owners+=len(layout)
                    for r in point['regions']:
                        records.setdefault((r['address'],r['size'],r['sha256'],tuple(r['pages'])),r);total+=r['size']
        for key,block in f['loader_pages'].items():self.assertEqual(hashlib.sha256(bytes.fromhex(block)).hexdigest(),key)
        for r in records.values():self.assertEqual(len(data(f,r)),r['size'])
        self.assertEqual((points,owners,total),(939,2514642,625415316))
        self.assertEqual(f['parser_owners_projection']['owners_checked'],owners);self.assertEqual(f['parser_projection']['bytes_checked'],total)
        pairs=self.call['comparisons'];self.assertEqual(len(pairs),465);self.assertEqual(collections.Counter(pair['before']['registers']['eip']for pair in pairs),dict(zip(COMPARISON_PCS,(117,116,116,116))))

    def test_every_old_new_memory_gp_fp_and_comparison_target(self):
        report=run(self.fixture)
        for key,value in(('cases',134),('cases_without_dispatch',133),('operations_checked',471),('comparisons_checked',465),('words_checked',78471426),('bytes_checked',313706724),('registers_checked',8007),('fp_bytes_checked',1149240),('differences',0)):self.assertEqual(report[key],value)

    def test_semantic_comparisons_drive_the_actual_caller_stores(self):
        a=self.point('parse');m=memory_for(self.fixture,a);frame=ParserCallers(m,a['registers']);warnings=[];parser=CommandStorage(m,Characters(self.call['entry']['characters']),lambda name:None,warnings.append)
        identity=parser.parse(frame.line,frame.records,[ScanHistory(None,None,None)for _ in range(15)],abi=frame)
        self.assertEqual(identity,-1);self.assertEqual(warnings,[]);self.assertEqual(frame.tokenizer_registers,self.call['tokenizer']['registers'])
        expected=[(pair['before']['registers']['esi'],COMPARISON_PCS.index(pair['before']['registers']['eip']))for pair in self.call['comparisons']]
        self.assertEqual(frame.comparisons,expected);self.assertEqual(m.u32(frame.frame-4),0)
        index=next(i for i,r in enumerate(CATALOG)if r[0]==-1);self.assertEqual(m.u32(frame.frame-8),index);self.assertEqual(m.u32(frame.frame-12),2*index)
        self.assertEqual(m.u32(frame.lookup_frame-16),frame.records)

    def test_changed_earlier_text_changes_lookup_events_without_target_data(self):
        a=self.point('parse')
        for text,identity,comparisons in((b'end',-1,466),(b'NOT_A_NATIVE_COMMAND',-2,468),(b'# comment',-3,0)):
            m=memory_for(self.fixture,a);line=m.u32(a['registers']['esp']+4);m.write(line,text+b'\0');frame=ParserCallers(m,a['registers']);parser=CommandStorage(m,Characters(self.call['entry']['characters']),lambda name:None,lambda message:None)
            with self.subTest(text=text):
                self.assertEqual(parser.parse(line,frame.records,[ScanHistory(None,None,None)for _ in range(15)],abi=frame),identity);self.assertEqual(len(frame.comparisons),comparisons)
                if comparisons:self.assertEqual(m.u32(frame.lookup_frame-16),frame.records)

    def test_earlier_registers_and_arguments_supply_prologue_and_push_words(self):
        a=self.point('parse');m=memory_for(self.fixture,a);r=dict(a['registers'],edi=0x11223344,esi=0x55667788,ebx=0xaabbccdd);result=parser_to_tokenizer(m,r);f=r['esp']-4
        self.assertEqual([m.u32(f-i)for i in(20,24,28)],[r['edi'],r['esi'],r['ebx']]);self.assertEqual(m.u32(f-32),f-4);self.assertEqual(result['esi'],m.u32(f+12))
        a=self.point('tokenized');m=memory_for(self.fixture,a);r=dict(a['registers'],eax=0xdeadbe81,esi=0x12345678);result=tokenizer_return_to_catalog(m,r)
        self.assertEqual(result['eax'],0xdeadbe81);self.assertEqual(m.u32(result['esp']+4),0x12345678);self.assertEqual(result['eflags']&0x80,0x80)
        a=capture.expand_point(self.fixture,self.call['comparisons'][0]['before']);m=memory_for(self.fixture,a);r=dict(a['registers'],edi=0x87654321);result=comparison_argument(m,r)
        self.assertEqual(m.u32(result['esp']),0x87654321);self.assertEqual(result['eflags'],r['eflags'])

    def test_argument_count_error_does_not_write_the_skipped_parent_local(self):
        a=self.point('parse')
        for text,identity,local in((b'SQUARE A B',-3,b'KEEP'),(b'SQUARE',0,bytes(4))):
            m=memory_for(self.fixture,a);line=m.u32(a['registers']['esp']+4);m.write(line,text+b'\0');f=a['registers']['esp']-4;m.write(f-16,b'KEEP');frame=ParserCallers(m,a['registers']);warnings=[];parser=CommandStorage(m,Characters(self.call['entry']['characters']),lambda name:None,warnings.append)
            with self.subTest(text=text):
                self.assertEqual(parser.parse(line,frame.records,[ScanHistory(None,None,None)for _ in range(15)],abi=frame),identity);self.assertEqual(m.read(f-16,4),local)

    def test_later_memory_gp_and_fp_are_only_comparison_targets(self):
        f=copy.deepcopy(self.fixture);c=copy.deepcopy(self.case);target=c['dispatch_calls'][0]['comparisons'][-1]['after'];point=copy.deepcopy(capture.expand_point(f,target));target['regions']=point['regions'];address=target['registers']['esp'];r=next(r for r in target['regions']if r['address']<=address<r['address']+r['size'])
        raw=bytearray(data(f,r));offset=address-r['address'];page=offset//4096;block=bytearray.fromhex(f['loader_pages'][r['pages'][page]]);block[offset%4096]^=1;key=hashlib.sha256(block).hexdigest();f['loader_pages'][key]=block.hex();r['pages'][page]=key;raw[offset]^=1;r['sha256']=hashlib.sha256(raw).hexdigest()
        target['registers']['eax']^=1;raw=bytearray.fromhex(target['xstate']);raw[0]^=1;target['xstate']=raw.hex()
        self.assertEqual(collections.Counter(d['kind']for d in compare(f,c)['differences']),{'parser-memory-word':1,'parser-register':1,'parser-fp-byte':1})

    def test_missing_earlier_catalog_word_has_no_later_fallback(self):
        c=copy.deepcopy(self.case);point=c['dispatch_calls'][0]['catalog'];a=copy.deepcopy(capture.expand_point(self.fixture,point));point['regions']=[r for r in a['regions']if r['address']!=0x80cbac0]
        self.assertTrue(any(d['kind']=='parser-runtime'and d['phase']=='catalog'for d in compare(self.fixture,c)['differences']))

    def test_complete_codec_and_invalid_overrides_are_checked(self):
        f=dict(cases=[dict(dispatch_calls=[dict(entry=dict(regions=[dict(address=16,data='00010203')]),end=dict(regions=[dict(address=16,data='04050607')]))])])
        capture.project(f);call=f['cases'][0]['dispatch_calls'][0];r=capture.expand_point(f,call['end'])['regions'][0];self.assertEqual(data(f,r),bytes.fromhex('04050607'))
        call['end']['region_changes']*=2
        with self.assertRaisesRegex(ValueError,'Repeated'):capture.expand_point(f,call['end'])
        call['end']['region_changes']=[(999,r)]
        with self.assertRaisesRegex(ValueError,'Invalid'):capture.expand_point(f,call['end'])
        f['loader_pages'][r['pages'][0]]='00000000'
        with self.assertRaises(ValueError):data(f,r)

    def test_continuing_frames_share_source_memory_and_comparison_events(self):
        from audit_command_transition_original import compare as continuing
        fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/printf_transition_original.json.gz').read_bytes()));case=next(c for c in fixture['cases']if(c['label'],c['cache_mode'])==(self.case['label'],self.case['cache_mode']));seen=[];original=ParserCallers.__init__
        def observe(frame,memory,registers):original(frame,memory,registers);seen.append(frame)
        with patch.object(ParserCallers,'__init__',observe):report,_,_,memory=continuing(fixture,case,return_state=True)
        self.assertEqual(len(seen),1);frame=seen[0];self.assertIs(frame.m,memory);self.assertEqual(frame.initial,self.call['parse']['registers']);self.assertEqual(frame.tokenizer_registers,self.call['tokenizer']['registers'])
        self.assertEqual(frame.comparisons,[(pair['before']['registers']['esi'],COMPARISON_PCS.index(pair['before']['registers']['eip']))for pair in self.call['comparisons']])
        self.assertFalse(any(d['kind']=='transition-runtime'for d in report['differences']));self.assertTrue(report['differences'],'Saved FP and all broader continuing targets remain required')


if __name__=='__main__':unittest.main()
