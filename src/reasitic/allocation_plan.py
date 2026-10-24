"""Native contact/cache and combined-network storage lifetimes.

This describes allocation/free order, not physical heap placement. It is not
yet used to allow out-of-range via writes. The reference paths are contacts.cpp,
potential_cache.cpp, potential_tables.cpp, potential_solver.cpp, solver.cpp,
filament_setup.cpp and combined_network.cpp /
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


def capacitance_prelude_storage(contact_counts,metals,substrates,fft_x,*,cache_mode,
                                file_bytes=304,buffer_bytes=4096):
    """Contact construction and successful/missing-cache storage lifetimes.

    Follows contacts.cpp, potential_cache.cpp and the allocated FFT scratch
    path. The malloc FILE/buffer lifetimes follow i386 glibc libio. FILE size
    and buffering are explicit ABI/filesystem inputs, not geometry cases.
    Cache modes are a valid disk cache, a missing disk cache, an already-current
    in-memory cache, or disabled disk caching. Invalid/truncated headers and
    allocation/I/O failures are not described by this successful-path plan.
    """
    counts=tuple(contact_counts)
    values=(*counts,metals,substrates,fft_x,file_bytes,buffer_bytes)
    if not counts or any(isinstance(v,bool)or not isinstance(v,int)or v<1 for v in values):
        raise ValueError('Invalid CAP prelude dimensions or storage sizes')
    if cache_mode not in ('warm','cold','memory','disabled'):raise ValueError('Unknown native cache mode')
    events=[]
    def allocate(name,size,allocator='array'):events.append(StorageEvent('allocate',name,size,allocator))
    def free(name,allocator='array'):events.append(StorageEvent('free',name,0,allocator))
    for i,count in enumerate(counts):
        allocate(f'contact_group.{i}',0x88,'scalar')
        # Each contact is prepended; final list order reverses allocation order.
        for j in reversed(range(count)):allocate(f'contact.{i}.{j}',0x3c,'scalar')
    if cache_mode=='memory':return events
    if cache_mode!='disabled':
        allocate('cache.reader.file',file_bytes,'malloc')
        if cache_mode=='warm':
            allocate('cache.header.substrates',40*substrates);allocate('cache.header.metals',236*metals)
            allocate('cache.reader.buffer',buffer_bytes,'malloc')
            free('cache.header.substrates');free('cache.header.metals')
            free('cache.reader.buffer','malloc')
        free('cache.reader.file','malloc')
        if cache_mode=='warm':return events
    for first in range(metals):
        for second in range(first,metals):
            name=f'cache.fft.{first}.{second}';allocate(name,32*fft_x);free(name)
    if cache_mode=='cold':
        allocate('cache.writer.file',file_bytes,'malloc');allocate('cache.writer.buffer',buffer_bytes,'malloc')
        free('cache.writer.buffer','malloc');free('cache.writer.file','malloc')
    return events


def capacitance_storage(contact_counts,conductors):
    """Folded CAP lifetimes, including the contact and workspace cleanup."""
    contact_counts=tuple(contact_counts)
    if not contact_counts or any(isinstance(n,bool)or not isinstance(n,int)or n<0 for n in (*contact_counts,conductors))or not conductors or len(contact_counts)<conductors or not sum(contact_counts):
        raise ValueError('Invalid native capacitance storage dimensions')
    events=[]
    def allocate(name,size):events.append(StorageEvent('allocate',name,size))
    def free(name,allocator='array',size=0):events.append(StorageEvent('free',name,size,allocator))
    contacts=sum(contact_counts);groups=len(contact_counts)
    allocate('cap.full',16*contacts*contacts)
    allocate('cap.inverse.pivots',4*contacts);allocate('cap.inverse.work',16*contacts)
    free('cap.inverse.work');free('cap.inverse.pivots')
    allocate('cap.reduced',16*groups*groups);allocate('cap.folded',16*groups*groups)
    allocate('cap.output',16*conductors*conductors)
    for i,count in enumerate(contact_counts):
        for j in range(count):free(f'contact.{i}.{j}','scalar',0x3c)
        free(f'contact_group.{i}','scalar',0x88)
    free('cap.folded');free('cap.reduced');free('cap.full')
    return events


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
    events=capacitance_storage(contact_counts,conductors)
    def allocate(name,size):events.append(StorageEvent('allocate',name,size))
    def free(name,allocator='array',size=0):events.append(StorageEvent('free',name,size,allocator))
    def symmetric_inverse(prefix,n):
        allocate(prefix+'.work',16*n);allocate(prefix+'.pivots',4*n);allocate(prefix+'.inverse_work',32*n)
        free(prefix+'.inverse_work');free(prefix+'.pivots');free(prefix+'.work')
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
