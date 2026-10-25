"""Folded-node source arrays in the same continuing geometry/network memory."""
import struct
from .memory import ComplexView
from .node_math import folded

# Fixed ET_EXEC bindings used by the original node instructions at
# 0x805489d..0x80549fe, independently of later port-record observations.
PORT_ADDRESSES=dict(y11=0x80d8da8,y12=0x80d8db8,y21=0x80d8dd8,y22=0x80d8de8)


class NodeStorage:
    def __init__(self,memory,addresses,nodes):
        self.memory=memory;self.addresses=addresses;self.nodes=nodes;self.sizes={};self.ports=None

    def allocated(self,event,address):
        self.sizes[event.name]=event.size
        if event.name!='node.pivots':self.memory.zero(address,event.size)

    def solve(self):
        n=self.nodes;memory=self.memory;addresses=self.addresses
        sizes={**self.sizes,'cap.output':16*n*n,'ind.output':16*n*n}
        ranges=sorted((addresses[name],addresses[name]+size,name)for name,size in sizes.items())
        if any(first[1]>second[0]for first,second in zip(ranges,ranges[1:])):
            raise NotImplementedError('Aliased folded-node factor/backsolve storage requires literal memory operations')
        def matrix(name):
            view=ComplexView(memory,addresses[name],n)
            return [[view.get(i,j)for j in range(n)]for i in range(n)]
        values={};self.ports,cap=folded(matrix('cap.output'),matrix('ind.output'),storage=values)
        ComplexView(memory,addresses['cap.output'],n).write(cap)
        ComplexView(memory,addresses['node.lu'],n).write(values.pop('lu'))
        memory.write(addresses['node.pivots'],struct.pack('<'+'i'*n,*values.pop('pivots')))
        for name,vector in values.items():memory.write(addresses['node.'+name],b''.join(struct.pack('<2d',z.real,z.imag)for z in vector))

    def publish_ports(self):
        """Store results after ordered workspace release, before node return."""
        if self.ports is None:raise ValueError('Node ports are unavailable before solving')
        for name in('y22','y11','y21','y12'):
            z=self.ports[name];self.memory.write(PORT_ADDRESSES[name],struct.pack('<2d',z.real,z.imag))
