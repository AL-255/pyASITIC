"""Native spatial commands applied to a freshly constructed device history."""
import copy,math
from .scene_heap import GeometryArena
from .command_numbers import length_um,angle_radians
from .paired_geometry import _name
from .retained_scalar import Real as R

ALIASES={}
for names in [('MOVE','MV'),('MOVEX','MVX'),('MOVEY','MVY'),('MOVETO','MVTO','SETORIG','SETORIGIN'),('ROTATE','ROT','TURN'),('FLIPV','FLIPVERT','VFLIP','VERTFLIP'),('FLIPH','FLIPHORZ','HFLIP','HORZFLIP'),('FLIP','REVERSE','REV','REORDER'),('COPY','CP','DUPLICATE','DUP'),('RENAME','REN','NEWNAME','NAME'),('BEFRIEND','FRIEND'),('UNFRIEND','DEFRIEND'),('PHASE','PH'),('ERASE','DEL','DELETE','RM'),('JOIN','ADD','MATE','COUPLE')]:
    ALIASES.update((name,names[0])for name in names)


class EditedScene(list):
    """Live winding order plus descriptor links retained across erasures."""
    pass


def apply_edits(shapes,technology,edits,*,with_links=False):
    """Replay original default-SNAP spatial commands without modifying inputs.

    MOVE/MOVETO keep native transformer/balun friends together. Rotation,
    reflection and segment-order reversal affect only the named winding.
    Source definitions remain intact so project exports can replay the history.
    """
    if not isinstance(edits,list):raise ValueError('Layout edits must be a list')
    paired=len(shapes)==2 and shapes[0].kind in('transformer','balun')
    generator_parameters=copy.deepcopy(shapes[0].parameters)if shapes else{}
    slots=list(shapes);live=list(range(len(slots)))
    friends=[1,0]if paired else[None]*len(slots)
    def needs_arena(op):
        if not isinstance(op,dict):return False
        command=ALIASES.get(str(op.get('command','')).upper())
        if command=='JOIN':
            sources=op.get('others',[op['other']]if 'other'in op else[])
            return isinstance(sources,list)and 1<=len(sources)<=11
        if command!='ERASE':return False
        indices=op.get('windings',[op.get('winding',0)])
        return isinstance(indices,list)and 1<=len(indices)<=10
    arena=GeometryArena()if any(needs_arena(op)for op in edits)else None
    addresses=[];segments=[];identities={};history=[]
    if arena is not None:
        for i,shape in enumerate(slots):
            address=arena.malloc(0xbc);addresses.append(address);identities[address]=i
            records=[arena.malloc(0xf0)for _ in shape.segments];segments.append(records);arena.write(shape,address,records)
    def allocate(shape):
        if arena is None:slot=len(slots);slots.append(shape);friends.append(None)
        else:
            address=arena.malloc(0xbc);slot=identities.get(address)
            if slot is None:
                slot=len(slots);identities[address]=slot;slots.append(None);friends.append(None);addresses.append(address);segments.append([])
            slots[slot]=shape;segments[slot]=[arena.malloc(0xf0)for _ in shape.segments];arena.write(shape,address,segments[slot])
        friends[slot]=None;live.append(slot)
    def release(slot,*,clear_peer=True):
        peer=friends[slot]
        if clear_peer and peer is not None:friends[peer]=None
        arena.write(slots[slot],addresses[slot],segments[slot])
        for address in segments[slot]:arena.free(address)
        arena.free(addresses[slot]);live.remove(slot);slots[slot].segments=[];segments[slot]=[]
    def sync():
        for i in live:arena.write(slots[i],addresses[i],segments[i])
    def reload():
        for i in live:arena.read(slots[i],addresses[i],segments[i])
    def length(op,key):return length_um(op[key],grid_size=.1)
    def winding(value):
        if isinstance(value,bool)or not isinstance(value,int)or not 0<=value<len(live):raise ValueError('Invalid edit winding')
        return value
    def name(value):
        result=_name(value)
        if not result or len(result.encode('utf8'))>79 or any(c in ' ,\t\n\r\v\f'for c in result):raise ValueError('Edit name must be one command token of 1–79 bytes')
        return result
    for op in edits:
        if not isinstance(op,dict):raise ValueError('Each layout edit must be an object')
        command=ALIASES.get(str(op.get('command','')).upper())
        if command is None:raise ValueError('Unknown spatial edit command')
        if command=='JOIN':
            sources=op.get('others',[op['other']]if 'other'in op else[])
            if not isinstance(sources,list)or not sources:raise ValueError('JOIN requires at least one source winding')
            indices=[op.get('winding',0),*sources];targets=[live[winding(i)]for i in indices[:12]]
            history.append([slots[live[i]].name if isinstance(i,int)and not isinstance(i,bool)and 0<=i<len(live)else f'winding {i}'for i in indices])
            target=slots[targets[0]]
            if len(indices)>12:target.warnings.append('Error:  Unknown argument type.');continue
            if len(set(targets))!=len(targets):target.warnings.append('Error:  Cannot join a spiral to itslef.');continue
            def metal(shape):
                return shape.segments[0].metal if shape.kind=='via'else technology.metal_index(shape.parameters.get('metal',len(technology.metals)-1))
            def compatible(via,other):
                encoded=metal(via);index=encoded-len(technology.metals)
                if not 0<=index<len(technology.vias):raise ValueError('Original JOIN indexes outside the via table for this converted VIA descriptor')
                layer=technology.vias[index]
                if metal(other)in(layer.top,layer.bottom):return True
                target.warnings.append(f'Error:  Via layer {index} can only join to metals {layer.top} or {layer.bottom}.');return False
            for source_slot in targets[1:]:
                source=slots[source_slot]
                if target.kind=='via'and not compatible(target,source):continue
                if source.kind=='via'and not compatible(source,target):continue
                if not target.segments or not source.segments:raise ValueError('Original JOIN faults on an empty segment chain')
                delta=[R(source.origin[axis])-R(target.origin[axis])for axis in range(2)]
                for segment in source.segments:
                    for point in segment.points:
                        for axis in range(2):point[axis]=float(delta[axis]+R(point[axis]))
                    target.segments.append(copy.deepcopy(segment));segments[targets[0]].append(arena.malloc(0xf0))
                if target.kind=='wire'and source.kind in('square','polygon'):
                    target.origin[:]=source.origin;target.parameters=copy.deepcopy(source.parameters)
                    target.parameters['turns']=float(R(source.parameters.get('turns',0))+R(.25));target.electrical_phase=source.electrical_phase
                target.kind='joined';release(source_slot,clear_peer=False)
            continue
        if command=='ERASE':
            indices=op.get('windings',[op.get('winding',0)])
            if not isinstance(indices,list)or not indices:raise ValueError('ERASE requires a nonempty winding list')
            # The native argument table's type-11 sentinel rejects the eleventh
            # argument before dispatch, leaving the entire scene unchanged.
            targets=[live[winding(i)]for i in indices[:10]]
            history.append([slots[live[i]].name if isinstance(i,int)and not isinstance(i,bool)and 0<=i<len(live)else f'winding {i}'for i in indices])
            if len(indices)>10:
                for i in live:slots[i].warnings.append('Error:  Unknown argument type.')
                continue
            if len(set(targets))!=len(targets):raise ValueError('The original ERASE faults on repeated winding arguments')
            for slot in targets:release(slot)
            continue
        index=winding(op.get('winding',0));slot=live[index];shape=slots[slot]
        peer=friends[slot];partner=slots[peer]if peer is not None else None
        history.append([shape.name])
        dangling=peer is not None and peer not in live
        if dangling and command in('MOVE','MOVEX','MOVEY','MOVETO'):sync()
        if command in('MOVE','MOVEX','MOVEY'):
            dx=length(op,'x')if command!='MOVEY'else None;dy=length(op,'y')if command!='MOVEX'else None
            for target in [shape,*([partner]if partner is not None and not dangling else[])]:
                if dx is not None:target.origin[0]=float(R(target.origin[0])+R(dx))
                if dy is not None:target.origin[1]=float(R(target.origin[1])+R(dy))
            if dangling:
                arena.store(addresses[slot]+0x54,shape.origin[0]);arena.store(addresses[slot]+0x5c,shape.origin[1])
                if dx is not None:arena.store(addresses[peer]+0x54,float(R(arena.number(addresses[peer]+0x54))+R(dx)))
                if dy is not None:arena.store(addresses[peer]+0x5c,float(R(arena.number(addresses[peer]+0x5c))+R(dy)))
                reload()
        elif command=='MOVETO':
            x,y=length(op,'x'),length(op,'y')
            if not 0<=x<=float(technology.chip.get('chipx',512))or not 0<=y<=float(technology.chip.get('chipy',512)):
                shape.warnings.append('Warning:  Moving spiral outside of chip area.')
            if partner is not None:
                # Native spills each previous origin difference to F64 before
                # adding the new F32 origin, rather than retaining one sum.
                dx=float(R(arena.number(addresses[peer]+0x54)if dangling else partner.origin[0])-R(shape.origin[0]));dy=float(R(arena.number(addresses[peer]+0x5c)if dangling else partner.origin[1])-R(shape.origin[1]))
            shape.origin[:]=[x,y]
            if dangling:
                arena.store(addresses[slot]+0x54,x);arena.store(addresses[slot]+0x5c,y)
                arena.store(addresses[peer]+0x54,float(R(dx)+R(x)));arena.store(addresses[peer]+0x5c,float(R(dy)+R(y)));reload()
            elif partner is not None:partner.origin[:]=[float(R(dx)+R(x)),float(R(dy)+R(y))]
        elif command=='COPY':
            requested=name(op['name'])
            if requested==shape.name:
                shape.warnings.append('Error:  Cannot copy to same name.');continue
            if any(slots[i].name==requested for i in live):
                # The native routine leaves an incomplete duplicate descriptor
                # after reporting this error. Reject the failed operation at
                # the API boundary rather than fabricate a valid new winding.
                raise ValueError('Error:  Cannot copy using a spiral name which is already in use.')
            target=technology.metal_index(op['metal'])if'metal'in op else None
            if('x'in op or'y'in op)and target is None:raise ValueError('COPY positions require a metal argument; use MOVETO to position a copy that keeps its metals')
            x=length(op,'x')if'x'in op else None
            if'y'in op and x is None:raise ValueError('COPY Y requires X')
            y=length(op,'y')if'y'in op else None
            copied=copy.deepcopy(shape);copied.name=requested;copied.parameters['name']=requested
            if x is not None and y is not None:copied.origin[:]=[x,y]
            if target is not None:
                copied.parameters['metal']=target;metal=technology.metals[target]
                for segment in copied.segments:
                    if segment.metal==target:continue
                    for point in segment.points:point[2]=metal.geometry_height
                    segment.metal=target;segment.thickness=metal.thickness;segment.primary_thickness=metal.thickness
            allocate(copied)
        elif command=='RENAME':
            requested=name(op['name'])
            if requested==shape.name:shape.warnings.append('Error:  Cannot rename to same name.')
            elif any(slots[i].name==requested for i in live):shape.warnings.append(f'Error:  {requested} already in use.')
            else:shape.name=requested;shape.parameters['name']=requested
        elif command=='BEFRIEND':
            other=live[winding(op['other'])];history[-1].append(slots[other].name);friends[slot]=other;friends[other]=slot
        elif command=='UNFRIEND':
            other=live[winding(op['other'])];history[-1].append(slots[other].name)
            if friends[slot]==other and friends[other]==slot:friends[slot]=friends[other]=None
            else:shape.warnings.append('Error:  Specified spirals are not friends.')
        elif command=='PHASE':
            value=op['phase']
            if isinstance(value,bool):raise ValueError('Phase must be a signed 32-bit integer')
            try:phase=int(value)
            except (TypeError,ValueError,OverflowError):raise ValueError('Phase must be a signed 32-bit integer')from None
            if not -(1<<31)<=phase<(1<<31):raise ValueError('Phase must be a signed 32-bit integer')
            previous=shape.electrical_phase
            if phase>=0 and previous<0 or phase<0 and previous>0:
                for segment in shape.segments:segment.reverse()
                shape.electrical_phase=phase
        elif command=='ROTATE':shape.rotate(angle_radians(op['angle']),force=True)
        elif command=='FLIPV':shape.reflect(0)
        elif command=='FLIPH':shape.reflect(1)
        else:
            shape.segments.reverse()
            if arena is not None:segments[slot].reverse()
        if any(not math.isfinite(v)for i in live for v in slots[i].origin):raise ValueError('Edited origin exceeds the finite native range')
    scene=EditedScene(slots[i]for i in live);positions={slot:i for i,slot in enumerate(live)}
    partners=[positions.get(friends[i])for i in live]
    scene.dangling_partners=[slots[friends[i]].name if friends[i]is not None and friends[i]not in positions else None for i in live]
    scene.history_targets=history;scene.generator_parameters=generator_parameters
    return(scene,partners)if with_links else scene
