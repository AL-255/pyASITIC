"""Source-computed numerical workspace stores before CAP matrix allocation.

FILE records/header arrays are being ported separately. No native buffer bytes
enter these calculations; they reuse production spectral tables and FFT.
"""
from .retained_scalar import Real
from .table_kernel import layer_coefficients
from .potential import _tables
from .file_buffer_storage import FileBytes,read_buffer,write_buffer
import struct


def table_storage(technology,frequency_hz,source,target,*,samples_only=False):
    """The complete table outputs and final grid FFT scratch before delete[]."""
    depths=[0.]*(len(technology.substrate)+1)
    for i in range(len(technology.substrate)-1,-1,-1):depths[i]=float(Real(depths[i+1])+technology.substrate[i]['t'])
    coefficients=layer_coefficients(technology.substrate,frequency_hz)
    metals=tuple((m.layer,float(Real(depths[m.layer])-m.height),m.thickness)for m in technology.metals)
    chip=technology.chip;nx=int(chip['fftx']);ny=int(chip['ffty'])
    return _tables(source,target,nx,ny,float(chip['chipx']),float(chip['chipy']),metals,coefficients,tuple(depths),include_storage=not samples_only,samples_only=samples_only)


def complex_bytes(values):return b''.join(struct.pack('<2d',z.real,z.imag)for z in values)


def cache_file(technology,frequency_hz):
    """Native fwrite/fread chunks; unported raw header records stay unknown."""
    nx=int(technology.chip['fftx']);ny=int(technology.chip['ffty'])
    chunks=[(struct.pack('<i',nx),4),(struct.pack('<i',ny),4),(struct.pack('<d',frequency_hz),8),
            (None,40*len(technology.substrate)),(None,236*len(technology.metals))]
    for source in range(len(technology.metals)):
        for target in range(source,len(technology.metals)):
            tx,ty,xy,scratch=table_storage(technology,frequency_hz,source,target)
            for values in (xy[:(nx+1)*(ny+1)],tx,ty):
                data=complex_bytes(values);chunks.append((data,len(data)))
    return FileBytes(chunks)


def store_file_buffer(memory,address,size,mode,technology,frequency_hz):
    file=cache_file(technology,frequency_hz)
    if mode=='cold':write_buffer(memory,address,size,file)
    elif mode=='warm':read_buffer(memory,address,size,file)
    else:raise ValueError('File buffers require a cold writer or warm reader')
