"""Read-only first upper impedance assembly in every produced UNJOIN model."""
import argparse,gzip,hashlib,json,subprocess,tempfile
from pathlib import Path
from capture_impedance_original import COMMANDS as ASSEMBLY,ORIGINAL_SHA256,LEGACY_SHA256
from capture_trailing_via_heap_original import native_environment

ROOT=Path(__file__).resolve().parents[1]
GUARD="""
import os
environment={item.split(b'=',1)[0].decode():item.split(b'=',1)[1].decode()for item in open('/proc/%d/environ'%gdb.selected_inferior().pid,'rb').read().split(b'\\0')if item}
if set(environment)-{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'}:raise RuntimeError('Unexpected native environment')
"""
COMMANDS=ASSEMBLY.replace('control_before=int(gdb.parse_and_eval',GUARD+'\ncontrol_before=int(gdb.parse_and_eval').replace("result=dict(n=n,", "result=dict(environment=environment,n=n,")


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);parser.add_argument('--output',type=Path,default=ROOT/'tests/fixtures/unjoin_assembly_original.json.gz');args=parser.parse_args();original=args.reference.resolve()/'run/asitic.linux.2.2'
    for path,digest in((original,ORIGINAL_SHA256),(args.reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Unexpected native binary: '+str(path))
    parents=[ROOT/'tests/fixtures'/name for name in('unjoin_sessions_original.json.gz','unjoin_plain_outcomes_original.json.gz')]
    sessions,plain=(json.loads(gzip.decompress(p.read_bytes()))for p in parents)
    if {c['label']for c in sessions['cases']}!={c['label']for c in plain['cases']if c['produced_model']}:raise ValueError('UNJOIN session coverage differs from its plain outcome cohort')
    cases=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-unjoin-assembly-')as directory:
        for index,c in enumerate(sessions['cases']):
            work=Path(directory)/str(index);work.mkdir()
            for name,value in(('process.tek',c['request']['technology']),('input.asit',c['script']),('answers.txt',c['stdin']),('capture.gdb',COMMANDS)):(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=native_environment(args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'assembly.json').exists()or'Python Exception'in run.stderr:raise RuntimeError(c['label']+': '+run.stdout[-1800:]+run.stderr[-1200:])
            result=json.loads((work/'assembly.json').read_text())
            if(result['control_before'],result['control_after'])!=(0x37f,0x37f):raise ValueError('Unexpected original control word')
            cases.append(dict(label=c['label'],request=c['request'],script=c['script'],stdin=c['stdin'],stdout=run.stdout,stderr=run.stderr,**result));print(c['label'],result['n'],'filaments captured',flush=True)
    fixture=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in parents},gdb_commands=COMMANDS,environment_overrides=native_environment(args.library_path),reference='Every produced model in the unchanged eight-session UNJOIN cohort. Read-only original first upper impedance assembly and every filament construction, retaining all defined upper entries, actual conductor inputs, material values, count stores and control words. Each observer stops at the first assembly return before inversion, then terminates its isolated inferior; it does not observe native command termination. All nine original plain outcomes, including the empty-winding fault, remain in the required parent archive. No numerical input, instruction, register, memory, allocation, CPU affinity or returned result is substituted.',cases=cases)
    with gzip.GzipFile(str(args.output),'wb',mtime=0)as stream:stream.write((json.dumps(fixture,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
