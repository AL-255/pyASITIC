"""Native storage lifetimes from folded CAP through the first node solve.

This describes allocation/free order, not physical heap placement. It is not
yet used to allow out-of-range via writes. The reference paths are
potential_solver.cpp, solver.cpp, filament_setup.cpp and combined_network.cpp /
later_analysis.cpp. The current plan covers successful inverse branches,
eddy disabled, and independent segment chains (no secondary groups).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class StorageEvent:
    action: str
    name: str
    size: int = 0
    allocator: str = 'array'


def combined_network_storage(contact_counts,conductors,filaments,vias,*,clone_segments=None):
    """Return source-generated array lifetimes and preexisting scalar frees.

    contact_counts follows the native linked contact-group order. No addresses,
    fixture values or selected geometry kinds enter this calculation. Physical
    placement also depends on allocations before this plan begins.
    """
    contact_counts=tuple(contact_counts)
    values=(*contact_counts,conductors,filaments,vias)
    if not contact_counts or any(isinstance(n,bool)or not isinstance(n,int)or n<0 for n in values)or not conductors or filaments<conductors:
        raise ValueError('Invalid native storage dimensions')
    if len(contact_counts)<conductors or not sum(contact_counts):raise ValueError('CAP needs contact groups for every conductor')
    if clone_segments is None:clone_segments=conductors+vias
    if isinstance(clone_segments,bool)or not isinstance(clone_segments,int)or clone_segments<conductors+vias:raise ValueError('Invalid cloned segment count')
    events=[]
    def allocate(name,size):events.append(StorageEvent('allocate',name,size))
    def free(name,allocator='array',size=0):events.append(StorageEvent('free',name,size,allocator))
    def general_inverse(prefix,n):
        allocate(prefix+'.pivots',4*n);allocate(prefix+'.work',16*n)
        free(prefix+'.work');free(prefix+'.pivots')
    def symmetric_inverse(prefix,n):
        allocate(prefix+'.work',16*n);allocate(prefix+'.pivots',4*n);allocate(prefix+'.inverse_work',32*n)
        free(prefix+'.inverse_work');free(prefix+'.pivots');free(prefix+'.work')
    contacts=sum(contact_counts);groups=len(contact_counts)
    allocate('cap.full',16*contacts*contacts);general_inverse('cap.inverse',contacts)
    allocate('cap.reduced',16*groups*groups);allocate('cap.folded',16*groups*groups)
    allocate('cap.output',16*conductors*conductors)
    for i,count in enumerate(contact_counts):
        for j in range(count):free(f'contact.{i}.{j}','scalar',0x3c)
        free(f'contact_group.{i}','scalar',0x88)
    free('cap.folded');free('cap.reduced');free('cap.full')
    allocate('ind.extra_segments',4*conductors)
    if vias:allocate('ind.via_indices',4*vias)
    allocate('ind.segments',4*conductors);allocate('ind.width_counts',4*conductors);allocate('ind.thickness_counts',4*conductors)
    allocate('ind.full',16*filaments*filaments);symmetric_inverse('ind.full_inverse',filaments)
    allocate('ind.zero_temporary',16*conductors*conductors);allocate('ind.output',16*conductors*conductors);free('ind.zero_temporary')
    if vias:
        symmetric_inverse('ind.reduced_inverse',conductors)
        allocate('ind.via_scratch',4*vias);free('ind.via_scratch')
        symmetric_inverse('ind.final_inverse',conductors)
    free('ind.full')
    for name in('segments','extra_segments','width_counts','thickness_counts'):free('ind.'+name)
    if vias:free('ind.via_indices')
    for i in range(clone_segments):free(f'geometry.segment.{i}','scalar',0xf0)
    free('geometry.descriptor','scalar',0xbc)
    return events
