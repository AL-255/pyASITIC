"""Compare identical cold/cached Pi2 sessions with the actual ASITIC binary.

The native cold/warm figures subtract process medians (0, 1 and 21 analyses).
Raw process samples are retained so startup and measurement noise are visible.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL_SHA256="72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference",type=Path,required=True)
    parser.add_argument("--native-library-path",required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--samples",type=int,default=3)
    args=parser.parse_args()
    if args.samples<1:parser.error("--samples must be positive")
    binary=args.reference.resolve()/"run/asitic.linux.2.2"
    if hashlib.sha256(binary.read_bytes()).hexdigest()!=ORIGINAL_SHA256:
        raise ValueError("Unexpected original executable checksum")
    sys.path.insert(0,str(ROOT/"src"))
    from reasitic.bridge import request_json
    fixture=json.loads((ROOT/"tests/fixtures/network.json").read_text())["cases"][2]
    construction=next(line for line in fixture["script"].splitlines() if line.startswith("SQUARE "))
    cases=[]
    for fft in (64,128):
        case=dict(fixture)
        if fft==128:case["technology"]=(args.reference/"run/tek/CMOS.tek").read_text()
        samples={}
        for count in (0,1,21):
            values=[]
            for _ in range(args.samples):
                with tempfile.TemporaryDirectory(prefix="pyasitic-native-benchmark-") as directory:
                    work=Path(directory)
                    (work/"process.tek").write_text(case["technology"])
                    prefix=case["script"].split("SAVEMAT")[0]+construction+"\n"
                    (work/"input.asit").write_text(prefix+"PI2 A 1\n"*count)
                    start=time.perf_counter()
                    result=subprocess.run([str(binary),"-g","-t","process.tek","-x","input.asit"],
                        cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.native_library_path,TERM="dumb",INPUTRC="/dev/null"),
                        input="EXIT\n",text=True,capture_output=True,start_new_session=True,timeout=60)
                    values.append(time.perf_counter()-start)
                    if result.returncode or result.stdout.count("Pi Model at")!=count:
                        raise RuntimeError(result.stdout+result.stderr)
            samples[count]=values
        medians={count:statistics.median(values) for count,values in samples.items()}
        payload={key:case[key] for key in ("kind","parameters","technology","frequency_hz","mesh","ground")}
        payload["action"]="pi2"
        python_times=[]
        for _ in range(3):
            start=time.perf_counter()
            result=json.loads(request_json(json.dumps(payload)))
            python_times.append(time.perf_counter()-start)
            if "error" in result:raise RuntimeError(result["error"])
        report=dict(fft=fft,native_process_samples=samples,native_process_medians=medians,
                    native_cold_seconds=medians[1]-medians[0],native_warm_seconds=(medians[21]-medians[1])/20,
                    python_seconds=python_times,request=payload,python_result=result["result"])
        cases.append(report)
        print(json.dumps({k:v for k,v in report.items() if k not in ("request","python_result","native_process_samples")}),flush=True)
    args.output.write_text(json.dumps(dict(original_sha256=ORIGINAL_SHA256,cases=cases),indent=2)+"\n")


if __name__=="__main__":main()
