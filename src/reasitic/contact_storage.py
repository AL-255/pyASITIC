"""Defined contact/group stores from contacts.cpp and potential_solver.cpp.

This materializes the prepared records at caller-supplied guest addresses.
It does not allocate, infer native addresses or initialize unwritten padding.
The temporary contact.index stack word remains unknown unless supplied by the
caller; matrix numbering later overwrites it independently of its old value.
"""
from dataclasses import dataclass
import struct
from .contact_geometry import groups


@dataclass(frozen=True)
class ContactRecord:
    bounds: tuple
    indices: tuple


@dataclass(frozen=True)
class GroupRecord:
    name: bytes
    coordinates: tuple
    cells: tuple
    metal: int
    contacts: tuple


def records(shape,technology,nx,ny,width,height,length_step,width_step,max_contacts=256,*,name=None):
    """Use the production contact geometry for every initialized record field."""
    text=(shape.name if name is None else name).encode('utf8').split(b'\0',1)[0]+b'\0'
    if len(text)>80:raise ValueError('A native contact group name must fit 80 bytes including NUL')
    metadata=[];bounds=[]
    contact_groups=groups(shape,technology,nx,ny,width,height,length_step,width_step,max_contacts,
                          lambda *indices:indices,observe=bounds.append,
                          observe_group=lambda coordinates,cells,metal:metadata.append((coordinates,cells,metal)))
    result=[];offset=0
    for contacts,(coordinates,cells,metal)in zip(contact_groups,metadata):
        physical=reversed(bounds[offset:offset+len(contacts)]);offset+=len(contacts)
        result.append(GroupRecord(text,coordinates,cells,metal,
                      tuple(ContactRecord(physical_bound,indices)for physical_bound,indices in zip(physical,contacts))))
    return tuple(result)


def write_prepared(memory,groups,addresses,*,history_index=None):
    """Materialize final prepared lists, preserving unwritten group bytes.

    addresses uses contact_group.i / contact.i.j identities in final linked
    order. Group +124 and name padding are untouched. An unknown incoming
    stack word overwrites contact +52 with unknown bytes, rather than reusing
    old heap data or silently selecting zero.
    """
    for i,group in enumerate(groups):
        address=addresses[f'contact_group.{i}']
        memory.write(address,group.name)
        memory.write(address+80,struct.pack('<4d',*group.coordinates))
        memory.write(address+112,struct.pack('<3i',*group.cells,group.metal))
        first=addresses[f'contact.{i}.0']if group.contacts else 0
        following=addresses[f'contact_group.{i+1}']if i+1<len(groups)else 0
        memory.write(address+128,struct.pack('<2I',first,following))
        for j,contact in enumerate(group.contacts):
            address=addresses[f'contact.{i}.{j}']
            memory.write(address,struct.pack('<4d5i',*contact.bounds,*contact.indices))
            if history_index is None:memory.write_unknown(address+52,4)
            else:memory.put_u32(address+52,history_index)
            memory.put_u32(address+56,addresses[f'contact.{i}.{j+1}']if j+1<len(group.contacts)else 0)


def number_contacts(memory,groups,addresses):
    """The linked-order numbering done by fill_contact_potential."""
    index=0
    for i,group in enumerate(groups):
        for j,contact in enumerate(group.contacts):
            memory.put_u32(addresses[f'contact.{i}.{j}']+52,index);index+=1


def number_groups(memory,groups,addresses):
    """The group +124 stores made while folding the inverted CAP matrix."""
    for i,group in enumerate(groups):memory.put_u32(addresses[f'contact_group.{i}']+124,i)
