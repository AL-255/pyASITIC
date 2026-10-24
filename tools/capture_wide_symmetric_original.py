"""Additional original matrix calls above the browser's filament budget."""
import argparse,hashlib,json,struct,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256,generated_matrix,upper_digest
ROOT=Path(__file__).resolve().parents[1]


def jobs():return [(288,'dominant'),(384,'dominant'),(384,'paired'),(512,'paired')]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);options=parser.parse_args()
    original=options.reference/'run/asitic.linux.2.2';legacy=options.reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,digest in ((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    source=ROOT/'tools/original_symmetric_probe.cpp';old=ROOT/'tests/fixtures/symmetric_large.json'
    flags=['-m32','-O2','-mfpmath=sse','-msse2','-fno-pie','-fno-pic','-fno-stack-protector','-fno-exceptions','-fno-rtti','-nostdlib','-no-pie','-Wl,-Ttext-segment=0x10000000']
    cases=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-wide-symmetric-')as directory:
        work=Path(directory);binary=work/'probe';data=work/'matrix.bin'
        subprocess.run(['g++',*flags,str(source),'/lib/i386-linux-gnu/libc.so.6','-Wl,--dynamic-linker=/lib/ld-linux.so.2','-o',str(binary)],check=True,capture_output=True)
        for n,kind in jobs():
            matrix=generated_matrix(n,kind);stride=n+2
            payload=b''.join(struct.pack('<2d',z.real,z.imag)for j in range(n)for z in [*(matrix[i][j]for i in range(n)),complex(1e120,-1e120),complex(1e120,-1e120)])
            data.write_bytes(payload)
            run=subprocess.run([str(binary),str(original),str(legacy),str(n),str(stride),str(data)],capture_output=True,text=True,start_new_session=True,timeout=180)
            if run.returncode:raise RuntimeError(str(run.returncode)+run.stderr[-1000:])
            record={}
            for line in run.stdout.splitlines():
                key,*values=line.split()
                if key in ('S','T','G'):record[key]=int(values[0])
                elif key=='P':record[key]=list(map(int,values))
                else:
                    numbers=list(map(float,values));pairs=[complex(*numbers[i:i+2])for i in range(0,len(numbers),2)]
                    assert len(pairs)==n*n;record[key]=[pairs[i:i+n]for i in range(0,len(pairs),n)]
            assert (record['S'],record['T'],record['G'])==(0,0,1)
            if kind=='paired':assert any(p<0 for p in record['P'])
            cases.append(dict(n=n,kind=kind,stride=stride,input_sha256=upper_digest(matrix),input_file_sha256=hashlib.sha256(payload).hexdigest(),P=record['P'],factor_sha256=upper_digest(record['F']),inverse_sha256=upper_digest(record['I']),padding_untouched=True))
            print(n,kind,'original complete factor/inverse digests',flush=True)
    result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),probe_source=source.read_text(),probe_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),compile_flags=flags,recipe='generated_matrix in capture_original_symmetric.py; upper_digest of complete row-wise upper triangle, little-endian binary64 components.',reference='Intact original ZSYTF2/ZSYTRI instructions with original numerical DSO imports. Larger driver backing only; original numerical instructions and constants unchanged. Every selected size is preserved.',cases=cases)
    (ROOT/'tests/fixtures/symmetric_wide_original.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
