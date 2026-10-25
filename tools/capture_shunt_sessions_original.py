"""Every selected JOINSHUNT model outcome, complete nodes and group geometry."""
import argparse,copy,os
from capture_join_sessions_original import jobs as source_jobs,capture_plain
import capture_copy_sessions_original as model
from capture_shunt_original import COMMANDS as GEOMETRY
from capture_shunt_original import command,update_names
from capture_trailing_via_heap_original import native_environment

NODE_OBSERVER=r'''
node_inputs=[]
class NodeInput(gdb.Breakpoint):
 def stop(self):
  def data(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
  def word(a):return struct.unpack('<I',data(a,4))[0]
  s=int(gdb.parse_and_eval('$esp'))&0xffffffff;n=word(s+12)
  if not 0<n<=256:raise RuntimeError('Invalid native node extent')
  node_inputs.append(dict(size=n,capacitance=data(word(s+4),16*n*n).hex(),inductance=data(word(s+8),16*n*n).hex()));return False
NodeInput('*0x8053e00',internal=True)
'''


def jobs():
    source={job[0]:job for job in source_jobs()}
    variants=[('wire/coarse','wire','coarse'),('wire/refined','wire','refined'),('wire/repeated','wire','repeated'),('wire/eddy','wire','eddy'),('wire/ground','wire','ground'),('wire/coupled','wire','coupled'),('wire/repeated-coupled','wire','repeated-coupled'),('square/coarse','square','coarse'),('square/refined','square','refined'),('square/eddy','square','eddy'),('balun/coarse','balun','coarse'),('balun/coupled','balun','coupled')]
    for label,kind,variant in variants:
        _,parent,r,prefix,stdin,names=copy.deepcopy(source['finite-'+kind+'/pi2']);n=len(names)
        edits=[dict(command='COPY',winding=0,name='c',metal='M2'),dict(command='JOINSHUNT',winding=0,others=[n])]
        if variant.startswith('repeated'):edits.extend([dict(command='COPY',winding=0,name='d',metal='M3'),dict(command='JOINSHUNT',winding=0,others=[n])])
        coupled=variant.endswith('coupled');r.update(action='calctrans'if coupled else'pi2',winding=0,edits=edits,eddy=variant=='eddy')
        if coupled or variant=='ground':
            edits.append(dict(command='COPY',winding=0,name='g',metal='M5'if variant=='repeated-coupled'else'M3',x=80,y=80))
            if coupled:r.update(first_winding=0,second_winding=n,termination_ohm=0)
            else:r['ground']={**{key:copy.deepcopy(r[key])for key in('kind','parameters','edits','native_interactive','native_keyword')if key in r},'winding':n}
        if variant=='refined':
            r['mesh'].update(length_cell=20,width_cell=3,thickness_cell=.5);prefix=prefix.replace('CELL 1000 1000 1000','CELL 20 3 .5',1)
        if variant=='eddy':prefix=prefix.replace('EDDY OFF','EDDY ON',1)
        yield label,parent,r,prefix,stdin,names


if __name__=='__main__':
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--library-path',required=True);args,_=parser.parse_known_args();os.environ.clear();os.environ.update(native_environment(args.library_path))
    accepted=capture_plain(output_name='shunt_plain_outcomes_original',job_source=jobs,command_source=command,names_source=update_names,description='All twelve selected unchanged JOINSHUNT -> Pi2/CALCTRANS/2PORT scripts run without GDB or replacements. Wire/square/balun, coarse/refined cells, repeated shunt joins, explicit ground, eddy and all three coupled requests retain every native outcome. produced_model means a report exists, not that it is finite.')
    model.PI_COMMANDS=model.PI_COMMANDS.replace('end\nrun -g',NODE_OBSERVER+'\nend\nrun -g').replace("open('raw.json'","result.update(nodes=node_inputs)\nopen('raw.json'")
    model.SNAPSHOT=GEOMETRY.split('python\n',1)[1].split('\nend\nrun',1)[0].replace('class Observe','class Snapshot').replace("Observe('*0x805bd40'","Snapshot('*0x804c620'").replace("  if i32(reg('esp')+4)!=224:return False\n",'').replace("'LD_LIBRARY_PATH','TERM'","'LD_LIBRARY_PATH','LD_PRELOAD','TERM'")
    model.main(output_name='shunt_sessions_original',job_source=lambda:iter(accepted),command_source=command,names_source=update_names,capture_cap_reference=False,description='Every produced report in the unchanged twelve-request JOINSHUNT plain cohort. Complete primary/secondary geometry and pointer records, raw model/Y/S/resonance, both actual CAP/inductive node-input arrays and native outcomes are retained by read-only observers. Coupled sprintf observer only records output; it does not replace numerical operations. All later words remain comparison targets, never runtime inputs. Minimal launch environment; no native numerical instruction, input, register, memory, allocation, result or outcome is substituted.')
