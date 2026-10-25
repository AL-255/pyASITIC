"""Read-only second branch solve, retaining the entire first/command history."""
import base64
from pathlib import Path
import capture_shunt_command_transition_original as command

# A fresh observer namespace watches the continuing inferior. It does not
# restart the program or write an inferior byte/register. All second-entry
# observations are later assertion targets, never runtime initialization.
SECOND_FIELDS=('contact_stack_entries','contact_storage','filament_context','console_inputs','console_calls','workspace_storage','cache_inputs','cache_outputs','libio_inputs','prelude_storage','prelude_final_heap','setup_events','setup_context','setup_output','prefix_events','allocator_states','events','contact_groups','matrices','via','node','post_events','post_states','post_buffers','post_node','post_output','post_driver')
SECOND_CODE=command.shunt.commands(Path('/unused')).split('python\n',1)[1].split('\nend\nrun ',1)[0]
OBSERVER=command.OBSERVER+'\nsecond=None\nsecond_namespace=None\nSECOND_CODE='+repr(base64.b64encode(SECOND_CODE.encode()).decode())+'\nSECOND_FIELDS='+repr(SECOND_FIELDS)+r'''
def second_begin():
 global second_namespace
 for breakpoint in gdb.breakpoints():breakpoint.enabled=False
 second_namespace={}
 exec(__import__('base64').b64decode(SECOND_CODE),second_namespace)
 entry=second_namespace['GeometrySetup']('*'+hex(reg('pc')),'begin');entry.stop();entry.enabled=False
 entry=second_namespace['PostNode']('*'+hex(reg('pc')),'driver');entry.stop();entry.enabled=False
 esp=reg('esp');driver=second_namespace['setup_context']['driver']
 second_namespace['setup_context']['entry']=dict(pc=reg('pc'),esp=esp,ebp=reg('ebp'),caller=u32(esp),arguments_data=mem(esp+4,28 if driver=='calctrans'else 20).hex())
def second_finish():
 global second
 n=second_namespace;signal=0
 if n['post_driver']is None and gdb.selected_inferior().pid:
  try:signal=int(gdb.parse_and_eval('$_siginfo.si_signo'))
  except gdb.error:pass
  n['post_snapshot']('post_fault')
 second={name:n[name]for name in SECOND_FIELDS}
 second.update(signal=signal,setup_pending=sum(map(len,n['setup_pending'].values())),setup_interfaces=len(n['setup_interfaces']),prefix_pending=sum(map(len,n['prefix_pending'].values())),prefix_interfaces=len(n['prefix_interfaces']),pending=sum(map(len,n['pending'].values())),post_pending=sum(map(len,n['post_pending'].values())),post_interfaces=len(n['post_interfaces']))
'''


def commands(directory,observer=OBSERVER):
    text=command.commands(directory,observer)
    before="signal=0\nif transition_end is None and gdb.selected_inferior().pid:"
    assert text.count(before)==1
    text=text.replace(before,"if transition_end is not None and gdb.selected_inferior().pid:\n second_begin()\n gdb.execute('continue')\n if second_namespace['node']is not None and second_namespace['post_driver']is None and gdb.selected_inferior().pid:gdb.execute('continue')\n second_finish()\n"+before)
    before='result=dict(transition_inputs='
    assert text.count(before)==1
    return text.replace(before,'result=dict(second=second,transition_inputs=')


def project_second(case,heap_pages,file_pages):
    second=case['second']
    if second is None:return
    for field in('allocator_states','post_states'):
        for state in second[field]:
            for region in state['memory_regions']:region.update(heap_pages(bytes.fromhex(region.pop('data'))))
    for record in second['post_buffers']:record.update(heap_pages(bytes.fromhex(record.pop('data'))))
    for region in second['setup_context']['memory_regions']:region.update(heap_pages(bytes.fromhex(region.pop('data'))))
    for record in second['cache_inputs']['initial_regions']:
        if not record['zero']:record.update(heap_pages(bytes.fromhex(record.pop('data'))))
    for record in second['cache_inputs']['files']:record.update(file_pages(bytes.fromhex(record.pop('data'))))
    for region in second['prelude_final_heap']or():region.update(heap_pages(bytes.fromhex(region.pop('data'))))


if __name__=='__main__':
    command.shunt.shunt.driver.main(fixture_name='shunt_second_driver_original.json.gz',parent_name='shunt_command_transition_original.json.gz',job_factory=command.shunt.shunt.jobs,
        observer=OBSERVER,command_builder=commands,state_fields=('allocator_states','post_states','transition_states'),buffer_fields=('post_buffers','transition_buffers'),project_extra_case=project_second,
        extra_metadata=dict(shunt_second_reference='Every unchanged fourteen-session/cold-warm script and plain outcome retained. Continue the same inferior after the first solve and outer port setup, through the second driver/node solve and return or original fault. A separate observer namespace reads second-stage geometry, complete heaps/cache tables/files, released arrays, calls and numerical targets. Every second-entry and later observation is an assertion target, never an execution input. No inferior instruction, byte, register, allocation result, return, numerical value or affinity is replaced.'))
