"""Native spatial commands applied to a freshly constructed device history."""
import copy,math
from .command_numbers import length_um,angle_radians
from .paired_geometry import _name
from .retained_scalar import Real as R

ALIASES={}
for names in [('MOVE','MV'),('MOVEX','MVX'),('MOVEY','MVY'),('MOVETO','MVTO','SETORIG','SETORIGIN'),('ROTATE','ROT','TURN'),('FLIPV','FLIPVERT','VFLIP','VERTFLIP'),('FLIPH','FLIPHORZ','HFLIP','HORZFLIP'),('FLIP','REVERSE','REV','REORDER'),('COPY','CP','DUPLICATE','DUP'),('RENAME','REN','NEWNAME','NAME'),('BEFRIEND','FRIEND'),('UNFRIEND','DEFRIEND'),('PHASE','PH')]:
    ALIASES.update((name,names[0])for name in names)


def apply_edits(shapes,technology,edits,*,with_links=False):
    """Replay original default-SNAP spatial commands without modifying inputs.

    MOVE/MOVETO keep native transformer/balun friends together. Rotation,
    reflection and segment-order reversal affect only the named winding.
    Source definitions remain intact so project exports can replay the history.
    """
    if not isinstance(edits,list):raise ValueError('Layout edits must be a list')
    paired=len(shapes)==2 and shapes[0].kind in('transformer','balun')
    partners=[1,0]if paired else[None]*len(shapes)
    def length(op,key):return length_um(op[key],grid_size=.1)
    def winding(value):
        if isinstance(value,bool)or not isinstance(value,int)or not 0<=value<len(shapes):raise ValueError('Invalid edit winding')
        return value
    def name(value):
        result=_name(value)
        if not result or len(result.encode('utf8'))>79 or any(c in ' ,\t\n\r\v\f'for c in result):raise ValueError('Edit name must be one command token of 1–79 bytes')
        return result
    for op in edits:
        if not isinstance(op,dict):raise ValueError('Each layout edit must be an object')
        command=ALIASES.get(str(op.get('command','')).upper())
        if command is None:raise ValueError('Unknown spatial edit command')
        index=winding(op.get('winding',0));shape=shapes[index]
        partner=shapes[partners[index]]if partners[index]is not None else None
        if command in('MOVE','MOVEX','MOVEY'):
            dx=length(op,'x')if command!='MOVEY'else None;dy=length(op,'y')if command!='MOVEX'else None
            for target in [shape,*([partner]if partner is not None else[])]:
                if dx is not None:target.origin[0]=float(R(target.origin[0])+R(dx))
                if dy is not None:target.origin[1]=float(R(target.origin[1])+R(dy))
        elif command=='MOVETO':
            x,y=length(op,'x'),length(op,'y')
            if not 0<=x<=float(technology.chip.get('chipx',512))or not 0<=y<=float(technology.chip.get('chipy',512)):
                shape.warnings.append('Warning:  Moving spiral outside of chip area.')
            if partner is not None:
                # Native spills each previous origin difference to F64 before
                # adding the new F32 origin, rather than retaining one sum.
                dx=float(R(partner.origin[0])-R(shape.origin[0]));dy=float(R(partner.origin[1])-R(shape.origin[1]))
            shape.origin[:]=[x,y]
            if partner is not None:partner.origin[:]=[float(R(dx)+R(x)),float(R(dy)+R(y))]
        elif command=='COPY':
            requested=name(op['name'])
            if requested==shape.name:
                shape.warnings.append('Error:  Cannot copy to same name.');continue
            if any(s.name==requested for s in shapes):
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
            shapes.append(copied);partners.append(None)
        elif command=='RENAME':
            requested=name(op['name'])
            if requested==shape.name:shape.warnings.append('Error:  Cannot rename to same name.')
            elif any(s.name==requested for s in shapes):shape.warnings.append(f'Error:  {requested} already in use.')
            else:shape.name=requested;shape.parameters['name']=requested
        elif command=='BEFRIEND':
            other=winding(op['other']);partners[index]=other;partners[other]=index
        elif command=='UNFRIEND':
            other=winding(op['other'])
            if partners[index]==other and partners[other]==index:partners[index]=partners[other]=None
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
        else:shape.segments.reverse()
        if any(not math.isfinite(v)for target in shapes for v in target.origin):raise ValueError('Edited origin exceeds the finite native range')
    return(shapes,partners)if with_links else shapes
