"""All independent native flags and fixed-program source provenance."""
import gzip,hashlib,json,os,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from capture_printf_integer_flags_native import requests,assembly
from audit_printf_integer_flags_native import run
from lift_printf_fp_original import LIBC_SHA256,RANGES
from reasitic.printf_fp_flow import operand,program


class PrintfInstructionFlagsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.probe=json.loads(gzip.decompress((ROOT/'tests/fixtures/printf_integer_flags_native.json.gz').read_bytes()))

    def test_every_declared_native_instruction_request(self):
        p=self.probe;cases=requests();self.assertEqual(len(cases),16528);self.assertEqual([{k:v for k,v in c.items()if k!='original'}for c in p['cases']],cases)
        source=assembly(cases);self.assertEqual(p['source'],source);self.assertEqual(p['source_sha256'],hashlib.sha256(source.encode()).hexdigest());self.assertEqual(p['cpu']['vendor_id'],'AuthenticAMD')
        self.assertEqual(set(p['environment']),{'PATH','HOME','LANG','LC_ALL'})

    def test_all_native_flags_and_registers(self):
        report=run(self.probe)
        if target:=os.environ.get('PYASITIC_PRINTF_INSTRUCTION_FLAGS_REPORT'):Path(target).write_text(json.dumps(report,indent=2)+'\n')
        self.assertEqual(report,dict(cases_required=16528,cases_checked=16528,registers_checked=82640,differences=[]))

    def test_changed_native_flags_remain_required(self):
        p=dict(self.probe,cases=list(self.probe['cases']));p['cases'][0]=dict(p['cases'][0],original=dict(p['cases'][0]['original'],eflags=p['cases'][0]['original']['eflags']^16))
        report=run(p);self.assertEqual(report['cases_checked'],16528);self.assertEqual(len(report['differences']),1);self.assertEqual(report['differences'][0]['name'],'eflags')

    def test_generated_original_program_and_complete_instruction_extents(self):
        raw=(ROOT/'src/reasitic/printf_fp_program.json').read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),'c72c83dbfccf4015b236fb1d7384aefdf0b886ca05a065827eb544390717df98')
        source=json.loads(raw);self.assertEqual(source['libc_sha256'],LIBC_SHA256);self.assertEqual(source['ranges'],[list(x)for x in RANGES]);self.assertEqual(len(program()),5314)
        for start,end,_ in RANGES:
            pc=start
            for address,length,_op,_args,raw in source['instructions']:
                if start<=address<end:self.assertEqual(address,pc);self.assertEqual(len(bytes.fromhex(raw)),length);pc+=length
            self.assertEqual(pc,end)

    def test_source_addresses_and_subregisters_are_explicit(self):
        self.assertEqual(operand('WORD PTR gs:0x14'),('m',16,1,20,()))
        self.assertEqual(operand('DWORD PTR [ebp+eax*4-0x10]'),('m',32,0,-16,(('ebp',1),('eax',4))))
        self.assertEqual(operand('ah'),('r','eax',8,8))
        with self.assertRaises(ValueError):operand('DWORD PTR [unknown+4]')


if __name__=='__main__':unittest.main()
