"""Read-only hardware watches identify both uninitialized header-date writers."""
import argparse,hashlib,json,os,subprocess,tempfile
from pathlib import Path
import capture_command_transition_original as transition

ROOT=Path(__file__).resolve().parents[1]
OBSERVER=transition.OBSERVER.replace('transition_active=True;return True','transition_active=True;start_transition_watch();return True')+r'''
transition_watch_log=[];transition_watch=None
class TransitionWatch(gdb.Breakpoint):
 def __init__(self,address):
  self.address=address;super().__init__('*(unsigned int*)'+hex(address),gdb.BP_WATCHPOINT,wp_class=gdb.WP_WRITE,internal=True)
 def stop(self):
  transition_watch_log.append(dict(address=self.address,pc=reg('pc'),esp=reg('esp'),ebp=reg('ebp'),value=u32(self.address),trace=gdb.execute('bt 4',to_string=True)))
  return False
def start_transition_watch():
 global transition_watch
 transition_watch=TransitionWatch(reg('esp')-(76 if setup_context['driver']=='pi2'else 72))
class StopTransitionWatch(gdb.Breakpoint):
 def stop(self):
  if transition_watch is not None:transition_watch.enabled=False
  return False
StopTransitionWatch('*0x808aafc',internal=True)
'''


def commands(debug_directory):
    return transition.commands(debug_directory,OBSERVER).replace('result=dict(transition_inputs=','result=dict(transition_watch_log=transition_watch_log,transition_inputs=')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,default=Path.home()/'github/asitic-re')
    parser.add_argument('--debug-directory',type=Path,required=True)
    parser.add_argument('--library-path',required=True)
    parser.add_argument('--output',type=Path,default=ROOT/'tests/fixtures/port_timestamp_writers_original.json')
    args=parser.parse_args();original=args.reference/'run/asitic.linux.2.2'
    script=commands(args.debug_directory)
    jobs=list(transition.node.console.driver.cache.libio.prelude.geometry.arena.lifetime.jobs())
    selected=[jobs[0],next(j for j in jobs if j['label']=='balun/head-tail/calctrans')]
    result=dict(original_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),observer=OBSERVER,gdb_commands=script,cases=[])
    for job in selected:
        with tempfile.TemporaryDirectory(prefix='pyasitic-trans-watch-')as directory:
            work=Path(directory)
            for name,data in (('process.tek',job['request']['technology']),('input.asit',job['script']),('answers.txt',job['stdin']),('capture.gdb',script)):(work/name).write_text(data)
            env=transition.node.console.driver.cache.libio.prelude.geometry.arena.lifetime.native_environment(args.library_path)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=env,capture_output=True,text=True,errors='surrogateescape',start_new_session=True,timeout=180)
            if run.returncode or not(work/'heap.json').exists()or'Python Exception'in run.stderr:raise RuntimeError(run.stdout[-1600:]+run.stderr[-1600:])
            data=json.loads((work/'heap.json').read_text())
            result['cases'].append(dict(label=job['label'],request=job['request'],script=job['script'],stdin=job['stdin'],registers=data['transition_inputs']['registers'],workspace_address=data['transition_inputs']['workspace_address'],watch=data['transition_watch_log'],calendar=data['transition_calendar'],stderr=run.stderr))
            print(job['label'],len(data['transition_watch_log']),flush=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
