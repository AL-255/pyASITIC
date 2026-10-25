"""Actual original helper and instruction stores for differing UNJOIN pairs."""
import argparse,gzip,hashlib,json,re,subprocess,tempfile
from pathlib import Path
from capture_mutual_command_traces_original import COMMANDS,ORIGINAL_SHA256,LEGACY_SHA256
from capture_trailing_via_heap_original import native_environment
from capture_unjoin_assembly_original import GUARD

ROOT=Path(__file__).resolve().parents[1]
PAIRS=((9,42),(9,45))
LABEL='balun/tail-other/calctrans'


def instruction_points(disassembly,parents):
    points={int(k,16):v for k,v in parents.items()}
    for match in re.finditer(r'^\s*([0-9a-f]+):\s+[0-9a-f ]+\s+(fyl2xp?1?|fpatan|fcos|fsin|f2xm1|fscale|frndint)\b',disassembly,re.M):
        address=int(match[1],16)
        if 0x80613bc<=address<0x8061b84:
            points.setdefault(address,[]).append((match[2],'before'));points.setdefault(address+2,[]).append((match[2],'after'))
    return points


def commands(ordinal,points):
    return COMMANDS.replace('TARGET',str(ordinal)).replace('MATHPOINTS',repr(points)).replace("entry=gdb.breakpoints()[0]",GUARD+"\nentry=gdb.breakpoints()[0]").replace('result=dict(input_bits=', 'result=dict(environment=environment,input_bits=')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);parser.add_argument('--output',type=Path,default=ROOT/'tests/fixtures/unjoin_mutual_traces_original.json.gz');args=parser.parse_args();original=args.reference.resolve()/'run/asitic.linux.2.2'
    for path,digest in((original,ORIGINAL_SHA256),(args.reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Unexpected native binary: '+str(path))
    paths=[ROOT/'tests/fixtures'/name for name in('unjoin_assembly_original.json.gz','unjoin_sessions_original.json.gz','mutual_command_traces_original.json')]
    assembly,models=(json.loads(gzip.decompress(p.read_bytes()))for p in paths[:2]);math=json.loads(paths[2].read_text());assembly=next(c for c in assembly['cases']if c['label']==LABEL);model=next(c for c in models['cases']if c['label']==LABEL)
    disassembly=subprocess.check_output(['objdump','-d',str(original)],text=True);points=instruction_points(disassembly,math['math_instruction_points']);cases=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-unjoin-mutual-')as directory:
        for index,(first,second)in enumerate(PAIRS):
            ordinal=sum(assembly['n']-1-i for i in range(first))+second-first-1;script=commands(ordinal,points);work=Path(directory)/str(index);work.mkdir()
            for name,value in(('process.tek',model['request']['technology']),('input.asit',model['script']),('answers.txt',model['stdin']),('capture.gdb',script)):(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=native_environment(args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'boundaries.json').exists()or'Python Exception'in run.stderr:raise RuntimeError(run.stdout[-1800:]+run.stderr[-1200:])
            result=json.loads((work/'boundaries.json').read_text())
            if result['input_bits']!=assembly['records'][first]['wire_bits']+assembly['records'][second]['wire_bits']:raise ValueError('Observed pair differs from the actual assembly inputs')
            if(result['control_before'],result['control_after'])!=(0x37f,0x37f):raise ValueError('Unexpected original control word')
            cases.append(dict(label=LABEL,first=first,second=second,script=model['script'],stdin=model['stdin'],stdout=run.stdout,stderr=run.stderr,gdb_commands=script,**result));print(first,second,len(result['events']),'original helper calls captured',flush=True)
    fixture=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},math_instruction_points={hex(k):v for k,v in points.items()},reference='Two differing upper entries identified by the complete eight-session UNJOIN assembly audit. The actual unchanged original script and independent original filament records supply pair identity. Every reached helper and selected elementary instruction store is retained. Read-only observers stop after the selected pair returns and terminate the isolated inferior; they do not observe native command termination. No numerical input, instruction, register, memory, allocation, CPU affinity or returned result is substituted. Native words are comparison targets only and never enter the runtime package.',cases=cases)
    with gzip.GzipFile(str(args.output),'wb',mtime=0)as stream:stream.write((json.dumps(fixture,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
