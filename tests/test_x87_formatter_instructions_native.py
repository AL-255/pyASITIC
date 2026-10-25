"""All native instruction states, including empty physical slots and Linux bytes."""
import gzip,hashlib,json,os,struct,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from capture_x87_formatter_instructions_native import requests,operations,assembly,OBSERVER
from audit_x87_formatter_instructions_native import run
import audit_x87_formatter_instructions_native as audit
from reasitic.x87_format_state import X87FormatState


class X87FormatterStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.probe=json.loads(gzip.decompress((ROOT/'tests/fixtures/x87_formatter_instructions_native.json.gz').read_bytes()))

    def test_all_independent_requests_and_native_program_provenance(self):
        p=self.probe;cases=requests();source,steps=assembly(cases);self.assertEqual(p['cases'],cases);self.assertEqual(len(cases),2416)
        self.assertEqual(source,p['source']);self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),p['source_sha256'])
        self.assertEqual([{k:v for k,v in s.items()if k!='after'}for s in p['steps']],steps)
        points=sorted({0,3,7,13}|{(i+1)*17 for i in range(len(cases))})
        self.assertEqual([o['step']for o in p['kernel_observations']],points);self.assertEqual(len(points),2420)
        self.assertEqual(p['gdb_observer'],OBSERVER+'\nfor index in '+repr(points)+':Point(index)\n')
        self.assertEqual(p['features'],p['supported_features']&p['xcr0'])
        self.assertEqual({(c['word']>>52)&2047 for c in cases},set(range(2048)))
        self.assertEqual({c['rounding']for c in cases},set(range(4)))
        self.assertEqual(set(p['environment']),{'PATH','HOME','LANG','LC_ALL','TERM','INPUTRC'})
        self.assertEqual(p['cpu']['vendor_id'],'AuthenticAMD')
        for point in p['kernel_observations']:
            fx=bytearray.fromhex(p['states'][p['steps'][point['step']]['after']['state']]);struct.pack_into('<Q',fx,464,p['features'])
            self.assertEqual(fx,bytes.fromhex(point['xstate'])[:512])

    def test_every_native_instruction_and_kernel_target(self):
        report=run(self.probe)
        if target:=os.environ.get('PYASITIC_X87_FORMAT_STATE_REPORT'):Path(target).write_text(json.dumps(report,indent=2)+'\n')
        self.assertEqual(report,dict(instructions_required=41072,instructions_checked=41072,fp_bytes_checked=21028864,registers_and_stores_checked=123216,kernel_fp_bytes_checked=5902360,differences=[]))

    def test_only_first_hardware_and_kernel_states_initialize_source(self):
        constructor=audit.X87FormatState;inputs=[]
        def track(image,**kwargs):inputs.append(image);return constructor(image,**kwargs)
        with patch.object(audit,'X87FormatState',track):report=run(self.probe)
        self.assertEqual(report['differences'],[])
        self.assertEqual(inputs,[bytes.fromhex(self.probe['states'][self.probe['steps'][0]['after']['state']]),bytes.fromhex(self.probe['kernel_observations'][0]['xstate'])])

    def test_changed_hardware_kernel_and_register_targets_remain_required(self):
        p=dict(self.probe,steps=list(self.probe['steps']),states=list(self.probe['states']),kernel_observations=list(self.probe['kernel_observations']))
        p['steps'][1]=dict(p['steps'][1],after=dict(p['steps'][1]['after'],eflags=p['steps'][1]['after']['eflags']^1))
        final=bytearray.fromhex(p['states'][p['steps'][-1]['after']['state']]);final[100]^=1;p['states'].append(final.hex())
        p['steps'][-1]=dict(p['steps'][-1],after=dict(p['steps'][-1]['after'],state=len(p['states'])-1))
        kernel=bytearray.fromhex(p['kernel_observations'][1]['xstate']);kernel[-1]^=1;p['kernel_observations'][1]=dict(p['kernel_observations'][1],xstate=kernel.hex())
        report=run(p);self.assertEqual(report['instructions_checked'],41072)
        self.assertEqual([(d['step'],d['kind'])for d in report['differences']],[(1,'eflags'),(3,'kernel-fp-byte'),(41072,'fp-byte')])

    def test_unimplemented_faults_and_inexact_stores_do_not_use_targets(self):
        initial=bytes.fromhex(self.probe['states'][self.probe['steps'][0]['after']['state']])
        with self.assertRaisesRegex(NotImplementedError,'pointer'):X87FormatState(initial,pointer_mode='unknown')
        with self.assertRaisesRegex(ValueError,'Truncated'):X87FormatState(initial[:64],pointer_mode='masked-error-pointers')
        cpu=X87FormatState(initial,pointer_mode='masked-error-pointers')
        with self.assertRaisesRegex(NotImplementedError,'underflow'):cpu.fst64()
        for _ in range(8):cpu.fld64(0)
        with self.assertRaisesRegex(NotImplementedError,'overflow'):cpu.fld64(0)
        cpu=X87FormatState(initial,pointer_mode='masked-error-pointers')
        with self.assertRaisesRegex(NotImplementedError,'Unmasked'):cpu.fldcw(cpu.control&~1)
        unmasked=bytearray(initial);struct.pack_into('<H',unmasked,0,cpu.control&~1)
        with self.assertRaisesRegex(NotImplementedError,'Unmasked'):X87FormatState(unmasked,pointer_mode='masked-error-pointers')
        compact=bytearray.fromhex(self.probe['kernel_observations'][0]['xstate']);struct.pack_into('<Q',compact,520,1<<63)
        with self.assertRaisesRegex(NotImplementedError,'Compacted'):X87FormatState(compact,pointer_mode='masked-error-pointers')
        cpu=X87FormatState(initial,pointer_mode='masked-error-pointers');cpu.fld64(0x3ff0000000000000);sig,exp=cpu.slots[cpu.top];cpu.slots[cpu.top]=(sig+1,exp)
        with self.assertRaisesRegex(NotImplementedError,'Inexact'):cpu.fst64()


if __name__=='__main__':unittest.main()
