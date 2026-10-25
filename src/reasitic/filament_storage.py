"""Native filament group/index/count tables and geometry cleanup ordering."""
import math,struct
from .solver import filament_counts


class FilamentLayout:
    """Source geometry metadata; addresses come from the same live memory."""
    def __init__(self,shape,metal_count):
        self.shape=shape;self.parents=list(shape.segments);self.conductors=[s for s in self.parents if s.metal<metal_count]
        self.group_segments=tuple(1+len(s.secondary)for s in self.conductors)
        self.clone_children=tuple(len(s.secondary)for s in self.parents)
        self.records=[record for parent in self.conductors for record in(parent,*parent.secondary)]
        self.via_indices=[];group=0
        for s in self.parents:
            if s.metal<metal_count:group+=1
            else:self.via_indices.append(group)

    def counts(self,mesh):
        return[filament_counts(s,mesh['width_cell'],mesh['thickness_cell'],mesh.get('max_width_cells',500))for s in self.records]

    def eddy_matrix_size(self,technology,mode):
        return 2*math.ceil(self.shape.parameters['turns'])if mode==1 and self.shape.kind=='square'and technology.eddy_layers else 0

    def before(self,name,memory,addresses,pointers,mesh):
        def integers(key,values):memory.write(addresses[key],b''.join(struct.pack('<i',v)for v in values))
        if name=='ind.segments':
            integers('ind.extra_segments',[n-1 for n in self.group_segments])
            if self.via_indices:integers('ind.via_indices',self.via_indices)
        elif name=='ind.width_counts':memory.write(addresses['ind.segments'],b''.join(struct.pack('<I',p)for p in pointers))
        elif name=='ind.full':
            counts=self.counts(mesh);integers('ind.width_counts',[y for y,z in counts]);integers('ind.thickness_counts',[z for y,z in counts])

    def pointers(self,memory,parents,*,addresses=None):
        if len(parents)!=len(self.parents):raise ValueError('Primary geometry pointer count differs from source records')
        result=[];conductors={id(s)for s in self.conductors}
        for i,(s,p)in enumerate(zip(self.parents,parents)):
            children=[]
            if memory is None:
                if s.secondary:raise ValueError('Secondary filament pointers require earlier source geometry memory')
            else:
                child=memory.u32(p+0xe8);seen=set()
                while child:
                    if child in seen:raise ValueError('Secondary filament pointer chain has a cycle')
                    seen.add(child);children.append(child);child=memory.u32(child+0xe8)
                if len(children)!=len(s.secondary):raise ValueError('Secondary geometry pointer count differs from source records')
            if addresses is not None:
                for j,child in enumerate(children):addresses[f'geometry.segment.{i}.secondary.{j}']=child
            if id(s)in conductors:result.extend([p,*children])
        return result
