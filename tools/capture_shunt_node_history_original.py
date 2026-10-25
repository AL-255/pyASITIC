"""Read-only full branch driver continuation through node solve and cleanup."""
import capture_shunt_driver_history_original as shunt
import capture_node_history_original as node

OBSERVER=(shunt.OBSERVER.replace('console_calls.append(record)',"record['post_events']=len(post_events);console_calls.append(record)")
          .replace('for event in events:\n',"for event in events+[e for e in post_events if e.get('returned')]:\n")
          +'\npost_events=[]'+node.OBSERVER.split('post_events=[]',1)[1])


def commands(directory,observer=OBSERVER):
    text=shunt.commands(directory,observer)
    before='signal=0\nif node is None and gdb.selected_inferior().pid:'
    assert text.count(before)==1
    text=text.replace(before,"if node is not None and gdb.selected_inferior().pid:gdb.execute('continue')\nsignal=0\nif post_driver is None and gdb.selected_inferior().pid:")
    before='result=dict(contact_stack_entries='
    assert text.count(before)==1
    return text.replace(before,"if post_seen and post_driver is None and gdb.selected_inferior().pid:post_snapshot('post_fault')\nresult=dict(post_events=post_events,post_states=post_states,post_buffers=post_buffers,post_node=post_node,post_output=post_output,post_driver=post_driver,post_pending=sum(map(len,post_pending.values())),post_interfaces=len(post_interfaces),contact_stack_entries=")


if __name__=='__main__':
    shunt.driver.main(fixture_name='shunt_node_history_original.json.gz',parent_name='shunt_driver_history_original.json.gz',job_factory=shunt.jobs,
                      observer=OBSERVER,command_builder=commands,state_fields=('allocator_states','post_states'),buffer_fields=('post_buffers',),
                      extra_metadata=dict(shunt_node_reference='Every fourteen-session/cold-warm shunt driver parent and plain outcome retained unchanged. Continue read-only from first node entry through first driver return or native fault. Observe complete node/release/return heaps, every released node and CAP/LMAT array byte, allocation/free calls, model console output and node/driver ports. Earlier driver/scene/cache/console/ESP inputs remain separate from all later assertion targets. No inferior call, numerical instruction, memory/register store, allocation result, affinity or return is replaced.'))
