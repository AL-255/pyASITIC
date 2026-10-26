"""Read-only lazy-lookup trace to diagnose full-history loader-counter gaps.

Uses the unchanged captured script, stdin, technology and initial cache bytes.
No trace result initializes source execution. Temporary reports stay outside
the runtime/source archives and do not replace the complete strict audit.
"""
import argparse,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from exit_fixture import read_fixture
from capture_cache_storage_original import expand_files
from audit_shunt_exit_original import compare
from reasitic.loader_lookup_storage import LoaderLookup

COMMANDS=r'''set pagination off
set confirm off
set breakpoint pending on
set debuginfod enabled off
handle SIGQUIT nostop noprint pass
python
import gdb,json,struct
active=False;records=[];drivers=0
def reg(n):return int(gdb.parse_and_eval('$'+n))&0xffffffff
def word(p):return struct.unpack('<I',bytes(gdb.selected_inferior().read_memory(p,4)))[0]
def text(p):return gdb.Value(p).cast(gdb.lookup_type('char').pointer()).string()
class Driver(gdb.Breakpoint):
 def stop(self):
  global active,drivers
  drivers+=1;active=True;records.append(dict(kind='driver',index=drivers,count=int(gdb.parse_and_eval('_rtld_global._dl_num_relocations'))));return False
class Lookup(gdb.Breakpoint):
 def stop(self):
  if active:
   s=reg('esp');map_=word(s+8);records.append(dict(kind='lookup',name=text(word(s+4)),map=text(word(map_+4)),trace=gdb.execute('bt 6',to_string=True),count=int(gdb.parse_and_eval('_rtld_global._dl_num_relocations'))))
  return False
class Exit(gdb.Breakpoint):
 def stop(self):
  records.append(dict(kind='exit',count=int(gdb.parse_and_eval('_rtld_global._dl_num_relocations'))));return False
Driver('*DRIVER_PC',internal=True);Lookup('_dl_lookup_symbol_x',internal=True);Exit('exit',internal=True)
end
run -g -t process.tek -x input.asit < answers.txt
python
open('lookup-trace.json','w').write(json.dumps(records,indent=2)+'\n')
end
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--debug-directory',type=Path,required=True)
    p.add_argument('--label',default='square/coarse');p.add_argument('--cache-mode',choices=('cold','warm'),default='warm');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    f=read_fixture(ROOT/'tests/fixtures/shunt_exit_original.json.gz');entry=next(c for c in f['cases']if(c['label'],c['cache_mode'])==(a.label,a.cache_mode))
    native=a.reference/'run/asitic.linux.2.2';legacy=a.reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,key in((native,'original_sha256'),(legacy,'legacy_sha256')):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=f[key]:raise ValueError('Changed pinned native image')
    # Same pinned source entry constants as capture_geometry_setup_original.
    pc={'pi2':0x8050b2c,'calctrans':0x8051280}[entry['setup_context']['driver']]
    commands='set debug-file-directory '+str(a.debug_directory)+'\n'+COMMANDS.replace('DRIVER_PC',hex(pc))
    with tempfile.TemporaryDirectory(prefix='pyasitic-exit-lookups-')as directory:
        work=Path(directory)
        files={name:text.encode()for name,text in(('process.tek',entry['request']['technology']),('input.asit',entry['script']),('answers.txt',entry['stdin']))}
        files.update(expand_files(f,entry))
        for name,raw in files.items():
            if Path(name).name!=name:raise ValueError('Invalid earlier launch file name')
            info=entry['initial_files'][name]
            if(len(raw),hashlib.sha256(raw).hexdigest())!=(info['size'],info['sha256']):raise ValueError('Changed captured native launch input')
            (work/name).write_bytes(raw)
        (work/'capture.gdb').write_text(commands)
        result=subprocess.run(['gdb','-q','-nx','-batch','-x','capture.gdb',str(native)],cwd=work,env=f['environment_overrides'],capture_output=True,start_new_session=True,timeout=180)
        if result.returncode or b'Python Exception'in result.stderr:raise RuntimeError((result.stdout+result.stderr).decode(errors='replace')[-4000:])
        observed=json.loads((work/'lookup-trace.json').read_text())
    calls=[];lookup=LoaderLookup.lookup
    def trace(loader,registers):
        s=registers['esp'];map_=loader.m.u32(s+8)
        calls.append(dict(name=loader._string(loader.m.u32(s+4)).decode(),map=loader._string(loader.m.u32(map_+4)).decode()))
        return lookup(loader,registers)
    with patch.object(LoaderLookup,'lookup',trace):report=compare(f,entry)
    a.output.write_text(json.dumps(dict(label=a.label,cache_mode=a.cache_mode,native=observed,source=calls,full_audit_differences=len(report['differences'])),indent=2)+'\n')
    print(dict(native_lookups=sum(r['kind']=='lookup'for r in observed),source_lookups=len(calls),strict_differences=len(report['differences'])))


if __name__=='__main__':main()
