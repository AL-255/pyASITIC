"""Read-only branch driver-to-next-command continuation on one native heap."""
import capture_shunt_node_history_original as shunt
import capture_command_transition_original as transition

OBSERVER=(shunt.OBSERVER
          .replace("for event in events+[e for e in post_events if e.get('returned')]:", "for event in events+[e for e in post_events+transition_events if e.get('returned')]:")
          .replace('global post_active,post_driver\n','global post_active,post_driver,transition_active,transition_console_start\n')
          .replace('post_active=False;return True','post_active=False;transition_console_start=len(console_calls);transition_active=True;return True')
          +'\ntransition_inputs=None'+transition.OBSERVER.split('transition_inputs=None',1)[1])


def commands(directory,observer=OBSERVER):
    text=shunt.commands(directory,observer)
    before='signal=0\nif post_driver is None and gdb.selected_inferior().pid:'
    assert text.count(before)==1
    text=text.replace(before,"if post_driver is not None and gdb.selected_inferior().pid:gdb.execute('continue')\nsignal=0\nif transition_end is None and gdb.selected_inferior().pid:")
    before='result=dict(post_events='
    assert text.count(before)==1
    return text.replace(before,"if transition_active and gdb.selected_inferior().pid:transition_snapshot('transition_fault')\ntransition_calls=[]if transition_console_start is None else console_calls[transition_console_start:]\nif transition_console_start is not None:console_calls=console_calls[:transition_console_start]\nresult=dict(transition_inputs=transition_inputs,transition_events=transition_events,transition_states=transition_states,transition_buffers=transition_buffers,transition_calls=transition_calls,transition_calendar=transition_calendar,transition_points=transition_points,transition_end=transition_end,transition_pending=sum(map(len,transition_pending.values())),transition_interfaces=len(transition_interfaces),post_events=")


if __name__=='__main__':
    shunt.shunt.driver.main(fixture_name='shunt_command_transition_original.json.gz',parent_name='shunt_node_history_original.json.gz',job_factory=shunt.shunt.jobs,
                            observer=OBSERVER,command_builder=commands,state_fields=('allocator_states','post_states','transition_states'),buffer_fields=('post_buffers','transition_buffers'),
                            extra_metadata=dict(shunt_command_reference='All fourteen unchanged shunt scripts, each cold/warm, and every original outcome retained. Earlier first-driver stack/script stream/port settings accompany the complete earlier driver inputs. Continue read-only past first driver return through outer script parsing and port-file setup to the next analysis driver or native fault. Every later heap, workspace, file, allocation, freed byte, call and calendar result is a comparison output. No inferior instruction, memory/register/return/allocation value, affinity or outcome is replaced.'))
