"""Second-call native cache reuse and disabled disk-cache allocation histories."""
import copy,hashlib
import capture_allocator_original as arena
import capture_cap_prelude_original as prefix
REFERENCE='Unchanged native wire scripts observed at their second CAP invocation, with TECHIO ON (reuse a current in-memory cache) or OFF (regenerate without disk IO). Both inherited disk-seed modes are retained. Read-only allocator observers; no numerical instructions, allocator calls or returned values are replaced.'

OBSERVER=prefix.OBSERVER.replace('prefix_events=[];prefix_active=False;','prefix_visits=0;prefix_events=[];prefix_active=False;').replace('global prefix_active,prefix_seen','global prefix_active,prefix_seen,prefix_visits').replace("if self.kind=='begin':\n   if prefix_seen:return False","if self.kind=='begin':\n   prefix_visits+=1\n   if prefix_seen or prefix_visits!=2:return False")
OBSERVER=OBSERVER.replace("state=allocator_states[-1];state['prefix_event_count']=len(prefix_events)","state=allocator_states[-1];state['prefix_event_count']=len(prefix_events)\n   state['cache_state']=dict(enabled=mem(0x80ce9a9,1)[0],dirty=mem(0x80ce9a8,1)[0],frequency_bits=mem(0x80ce578,8).hex(),visit=prefix_visits)")


def commands(directory,observer=OBSERVER):
    text=prefix.commands(directory,observer)
    before='if cap_frame is not None:return False'
    assert text.count(before)==1
    return text.replace(before,'if cap_frame is not None or not prefix_seen:return False')


def jobs():
    base=next(arena.lifetime.jobs());technology=base['request']['technology'];parent=base['parent']
    for mode,enabled in (('memory','ON'),('disabled','OFF')):
        parameters=dict(name='A',length=40,width=6,metal='M4',angle=0,phase=1,x=8,y=8)
        request=dict(action='pi2',kind='wire',parameters=parameters,technology=technology,frequency_ghz=.25,frequency_hz=250e6,eddy=False,winding=0,native_keyword=True,native_mesh=True,mesh=dict(length_cell=1000,width_cell=1000,thickness_cell=1000,capacitance_length_cell=1000,capacitance_width_cell=1000))
        script=f'CELL 1000 1000 1000\nCCELL 1000 1000\nEDDY OFF\nTECHIO {enabled}\nWIRE NAME=A:LEN=40:WID=6:METAL=M4:ORIENT=0:PHASE=1:XORG=8:YORG=8\nPI2 A .25\nPI2 A .25\n2PORT A .25 .25 1 S RECT SLOW s.out\n'
        yield dict(label='wire-second/'+mode,parent=parent,request=copy.deepcopy(request),script=script,stdin='quit\n',variant=mode,prelude_cache_mode=mode)


if __name__=='__main__':
    parent=arena.lifetime.ROOT/'tests/fixtures/cap_prelude_original.json.gz'
    arena.main(observer=OBSERVER,fixture_name='cap_prelude_modes_original.json.gz',command_builder=commands,job_factory=jobs,extra_metadata=dict(prelude_modes_parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),reference=REFERENCE))
