"""Native spatial commands applied to a freshly constructed device history."""
import math
from .command_numbers import length_um,angle_radians
from .retained_scalar import Real as R

ALIASES={}
for names in [('MOVE','MV'),('MOVEX','MVX'),('MOVEY','MVY'),('MOVETO','MVTO','SETORIG','SETORIGIN'),('ROTATE','ROT','TURN'),('FLIPV','FLIPVERT','VFLIP','VERTFLIP'),('FLIPH','FLIPHORZ','HFLIP','HORZFLIP'),('FLIP','REVERSE','REV','REORDER')]:
    ALIASES.update((name,names[0])for name in names)


def apply_edits(shapes,technology,edits):
    """Replay original default-SNAP spatial commands without modifying inputs.

    MOVE/MOVETO keep native transformer/balun friends together. Rotation,
    reflection and segment-order reversal affect only the named winding.
    Source definitions remain intact so project exports can replay the history.
    """
    if not isinstance(edits,list):raise ValueError('Layout edits must be a list')
    paired=len(shapes)==2 and shapes[0].kind in('transformer','balun')
    def length(op,key):return length_um(op[key],grid_size=.1)
    for op in edits:
        if not isinstance(op,dict):raise ValueError('Each layout edit must be an object')
        command=ALIASES.get(str(op.get('command','')).upper())
        if command is None:raise ValueError('Unknown spatial edit command')
        index=op.get('winding',0)
        if isinstance(index,bool)or not isinstance(index,int)or not 0<=index<len(shapes):raise ValueError('Invalid edit winding')
        shape=shapes[index];partner=shapes[1-index]if paired else None
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
                partner.origin[:]=[float(R(dx)+R(x)),float(R(dy)+R(y))]
            shape.origin[:]=[x,y]
        elif command=='ROTATE':shape.rotate(angle_radians(op['angle']),force=True)
        elif command=='FLIPV':shape.reflect(0)
        elif command=='FLIPH':shape.reflect(1)
        else:shape.segments.reverse()
        if any(not math.isfinite(v)for target in shapes for v in target.origin):raise ValueError('Edited origin exceeds the finite native range')
    return shapes
