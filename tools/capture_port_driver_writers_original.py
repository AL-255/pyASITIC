"""Read-only hardware provenance for the sweep driver's retained flag padding."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
import capture_shunt_command_transition_original as command

ROOT=Path(__file__).resolve().parents[1]
OBSERVER=command.OBSERVER.replace('transition_active=True;return True','transition_active=True;start_driver_watch();return True')+r'''
driver_watch_log=[];driver_watch=None
class DriverWatch(gdb.Breakpoint):
 def __init__(self,address):
  self.address=address;super().__init__('*(unsigned int*)'+hex(address),gdb.BP_WATCHPOINT,wp_class=gdb.WP_WRITE,internal=True)
 def stop(self):
  driver_watch_log.append(dict(address=self.address,pc=reg('pc'),esp=reg('esp'),ebp=reg('ebp'),value=u32(self.address),registers={k:reg(k)for k in('eax','ebx','ecx','edx','esi','edi')},trace=gdb.execute('bt 6',to_string=True)))
  return False
def start_driver_watch():
 global driver_watch
 driver_watch=DriverWatch(reg('ebp')-0x444-12-8-8-0x28-12-4-24-8-20)
class StopDriverWatch(gdb.Breakpoint):
 def stop(self):
  if driver_watch is not None and transition_active:driver_watch.enabled=False
  return False
StopDriverWatch('*0x8050b2c',internal=True)
'''


def commands(directory):
    return command.commands(directory,OBSERVER).replace('result=dict(transition_inputs=','result=dict(driver_watch_log=driver_watch_log,transition_inputs=')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,default=Path.home()/'github/asitic-re');parser.add_argument('--debug-directory',type=Path,required=True);parser.add_argument('--library-path',required=True);parser.add_argument('--output',type=Path,default=ROOT/'tests/fixtures/port_driver_writers_original.json');args=parser.parse_args()
    original=args.reference/'run/asitic.linux.2.2';script=commands(args.debug_directory)
    jobs=list(command.shunt.shunt.jobs());selected=[next(j for j in jobs if j['label']==label)for label in('wire/coarse','square/coarse','unequal-branch/asymmetric')]
    result=dict(original_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),observer=OBSERVER,gdb_commands=script,cases=[])
    for job in selected:
        with tempfile.TemporaryDirectory(prefix='pyasitic-port-driver-watch-')as directory:
            work=Path(directory)
            for name,data in(('process.tek',job['request']['technology']),('input.asit',job['script']),('answers.txt',job['stdin']),('capture.gdb',script)):(work/name).write_text(data)
            factory=command.shunt.shunt.driver.cache.libio.prelude.geometry.arena.lifetime.native_environment
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=factory(args.library_path),capture_output=True,text=True,errors='surrogateescape',start_new_session=True,timeout=180)
            if run.returncode or not(work/'heap.json').exists()or'Python Exception'in run.stderr:raise RuntimeError(run.stdout[-1600:]+run.stderr[-1600:])
            data=json.loads((work/'heap.json').read_text())
            result['cases'].append(dict(label=job['label'],request=job['request'],script=job['script'],stdin=job['stdin'],registers=data['transition_inputs']['registers'],watch=data['driver_watch_log'],libc_base=data['libio_inputs']['libc_base'],stderr=run.stderr))
            print(job['label'],len(data['driver_watch_log']),flush=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
