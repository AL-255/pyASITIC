"""Successful combined-network stores into one shared guest memory.

Inputs are source-computed buffers, records and preexisting geometry addresses.
Numerical workspace/pivot values not yet generated remain explicitly unknown.
This is not connected to production trailing-via execution.
"""
import struct
from .memory import Memory,ComplexView
from .contact_storage import write_prepared,number_contacts,number_groups
from .solver import filament_counts


def symmetric_inverse_storage(matrix,prefix):
    """Successful unblocked symmetric wrapper's pivots and final work arrays."""
    from .symmetric import factor_symmetric_upper
    factors,pivots=factor_symmetric_upper(matrix);n=len(matrix)
    last=n-1 if pivots[-1]>0 else n-2
    return {prefix+'.pivots':tuple(pivots),
            prefix+'.work':(complex(64*n if n>64 else 1,0),*(0j for _ in range(n-1))),
            prefix+'.inverse_work':(*(factors[i][n-1]for i in range(last)),*(0j for _ in range(2*n-last)))}


class StorageHistory:
    def __init__(self,heap,addresses,*,initial_regions,key,contacts,capacitance,impedance,
                 technology,mesh,geometry_addresses,via_records,termination_boundary=None,termination_ohm=0,inverse_storage=None,geometry_shape_address=None,memory=None,capacitance_producer=None):
        if memory is not None:
            if initial_regions:raise ValueError('A continuous history cannot seed replacement memory')
            heap.require_cache_memory(memory,key)
        self.heap=heap;self.memory=Memory(heap.address_space)if memory is None else memory;self.addresses=addresses
        if impedance.full_y is None:raise ValueError('Storage history requires retained full inverse data')
        self.contacts=contacts;self.capacitance=capacitance;self.impedance=impedance
        self.capacitance_producer=capacitance_producer
        self.technology=technology;self.mesh=mesh;self.geometry_addresses=geometry_addresses;self.via_records=via_records
        self.termination_boundary=termination_boundary;self.cap_written=False;self.sizes={}
        self.termination_ohm=termination_ohm
        self.inverse_storage={}if inverse_storage is None else inverse_storage
        if memory is None:
            for address,data in initial_regions:self.memory.write(address,data)
            heap.observe_cache_stores(self.memory,key)
            write_prepared(self.memory,contacts,addresses)
            for segment,address in zip(impedance.meshed.segments,geometry_addresses):
                self.memory.write(address,struct.pack('<d',segment.start[0]))
            if geometry_shape_address is not None and contacts:self.memory.write(geometry_shape_address,contacts[0].name)

    def matrix(self,name,values):
        ComplexView(self.memory,self.addresses[name],len(values)).write(values)

    def integers(self,name,values):
        self.memory.write(self.addresses[name],b''.join(struct.pack('<i',value)for value in values))

    def before(self,event):
        name=event.name;allocate=event.action=='allocate'
        if not self.cap_written and name.startswith('contact'):
            for buffer,matrix in self.capacitance.items():self.matrix(buffer,matrix)
            if self.capacitance_producer is None:
                number_contacts(self.memory,self.contacts,self.addresses);number_groups(self.memory,self.contacts,self.addresses)
            self.cap_written=True
        if allocate and name=='ind.extra_segments'and self.termination_boundary is not None:
            from .retained_scalar import Real as R
            view=ComplexView(self.memory,self.addresses['cap.output'],len(self.capacitance['cap.output']))
            k=self.termination_boundary;old=view.get(k,k)
            shunt=R(1e15)if R(self.termination_ohm)<R(float.fromhex('0x1.b7cdfd9d7bdbbp-34'))else R(1)/R(self.termination_ohm)
            view.set(k,k,complex(float(shunt+R(old.real)),old.imag+0.))
        if allocate and name=='ind.segments':
            n=len(self.impedance.groups);self.integers('ind.extra_segments',[0]*n)
            if self.via_records:self.integers('ind.via_indices',[index for index,record in self.via_records])
        if allocate and name=='ind.width_counts':
            metal_count=len(self.technology.metals)
            pointers=[p for segment,p in zip(self.impedance.meshed.segments,self.geometry_addresses)if segment.metal<metal_count]
            self.memory.write(self.addresses['ind.segments'],b''.join(struct.pack('<I',p)for p in pointers))
        if allocate and name=='ind.full':
            conductors=[s for s in self.impedance.meshed.segments if s.metal<len(self.technology.metals)]
            counts=[filament_counts(s,self.mesh['width_cell'],self.mesh['thickness_cell'],self.mesh.get('max_width_cells',500))for s in conductors]
            self.integers('ind.width_counts',[y for y,z in counts]);self.integers('ind.thickness_counts',[z for y,z in counts])
        if allocate and name=='ind.reduced_inverse.work':self.matrix('ind.output',self.impedance.reduced_y)
        if not allocate:
            # With no vias/eddy and admittance output, native LMAT reduces
            # directly to Y and skips both small-matrix inverse wrappers.
            if name=='ind.full'and not self.via_records:self.matrix('ind.output',self.impedance.reduced_y)
            # Native factor/inverse routines fill pivots and overwrite scratch
            # elements. Do not pretend that constructor zeros are final values.
            if name.endswith(('.pivots','.work','.inverse_work')):
                self.memory.write_unknown(self.addresses[name],self.sizes[name])
                if name in self.inverse_storage:
                    values=self.inverse_storage[name]
                    if name.endswith('.pivots'):self.integers(name,values)
                    else:self.memory.write(self.addresses[name],b''.join(struct.pack('<2d',z.real,z.imag)for z in values))
            if name=='ind.full_inverse.inverse_work':
                p=self.impedance;n=p.filaments
                # Native assembly writes only the upper triangle; the
                # constructor's lower-triangle zeros survive this inverse.
                self.matrix('ind.full',[[p.full_y[i][j]if i<=j else 0j for j in range(n)]for i in range(n)])
            if name=='ind.reduced_inverse.inverse_work':self.matrix('ind.output',self.impedance.reduced_z)
            if name=='ind.final_inverse.inverse_work':self.matrix('ind.output',self.final_y)

    def allocated(self,event,address):
        self.sizes[event.name]=event.size
        name=event.name
        complex_vector=(name in ('cap.full','cap.reduced','cap.folded','cap.output','ind.full','ind.zero_temporary','ind.output')
                        or name.endswith(('.work','.inverse_work')))
        if complex_vector:self.memory.zero(address,event.size)
        if name=='cap.full'and self.capacitance_producer is not None:
            number_contacts(self.memory,self.contacts,self.addresses)
            view=ComplexView(self.memory,address,sum(len(group.contacts)for group in self.contacts))
            self.capacitance.update(self.capacitance_producer(view))
        if name=='cap.reduced'and self.capacitance_producer is not None:number_groups(self.memory,self.contacts,self.addresses)

    def begin_stamps(self):
        metal_count=len(self.technology.metals)
        pointers=[p for segment,p in zip(self.impedance.meshed.segments,self.geometry_addresses)if segment.metal>=metal_count]
        if pointers:self.memory.write(self.addresses['ind.via_scratch'],b''.join(struct.pack('<I',p)for p in pointers))

    def finish_stamps(self):
        from .symmetric import inverse_symmetric
        n=len(self.impedance.groups);view=ComplexView(self.memory,self.addresses['ind.output'],n)
        matrix=[[view.get(i,j)for j in range(n)]for i in range(n)]
        self.inverse_storage.update(symmetric_inverse_storage(matrix,'ind.final_inverse'))
        self.final_y=inverse_symmetric(matrix)
