"""Original cache-table stores at caller-supplied initial guest allocations.

Spectral generation and FFTs reuse the production numerical kernels. Ordered
stores preserve the native nx+1 generation / ny+1 transform stride mismatch,
including writes outside declared arrays. No future table/heap observation is
an execution input. Initial cache allocations and external disk files are
explicit caller state, pending full process-startup integration.
"""
import hashlib,struct
from .prelude_storage import table_storage,complex_bytes
from .fft import _fft,_transform_grid
from .file_buffer_storage import FileBytes,read_buffer,write_buffer
from .memory import ComplexArray
from .table_kernel import layer_coefficients


def initial_regions(inputs):
    result=[]
    for region in inputs['initial_regions']:
        data=bytes(region['size'])if region['zero']else bytes.fromhex(region['data'])
        if len(data)!=region['size']or hashlib.sha256(data).hexdigest()!=region['sha256']:raise ValueError('Incomplete initial cache storage')
        result.append((region['address'],data))
    return result


class CacheStorage:
    def __init__(self,memory,inputs,technology,frequency_hz,files=()):
        self.memory=memory;self.inputs=inputs;self.technology=technology;self.frequency=frequency_hz
        self.nx=int(inputs['nx']);self.ny=int(inputs['ny']);self.metals=int(inputs['metals']);self.pending=None
        self.files=tuple(files);self.loaded=None

    def index(self,source,target):return source*self.metals-source*(source-1)//2+target-source
    def address(self,name,index):return self.memory.u32(self.inputs['arrays'][name]['pointer_address']+4*index)
    def __call__(self,source,target):
        index=self.index(source,target);nx,ny=self.nx,self.ny
        return tuple(ComplexArray(self.memory,self.address(name,index),count)for name,count in (('x',2*nx),('y',2*ny),('xy',max((nx+1)*(ny+1),nx*(nx+1)+ny+1))))

    def can_batch(self,address,size):
        # Rectangular contact reads can go beyond declared XY storage. Keep
        # those reads literal, including any aliases with the output matrix.
        if self.nx!=self.ny:return False
        count=self.metals*(self.metals+1)//2
        for group in self.inputs['arrays'].values():
            ranges=[(group['pointer_address'],4*count)]
            ranges.extend((self.memory.u32(group['pointer_address']+4*i),group['size'])for i in range(count))
            if any(start<address+size and address<start+length for start,length in ranges):return False
        return True

    def write_coefficients(self):
        """Native CAP stores these before opening/generating a cache file."""
        values=layer_coefficients(self.technology.substrate,self.frequency)
        self.memory.write(self.inputs['coefficient_address'],complex_bytes(values))
    def _get(self,address,index):return complex(*struct.unpack('<2d',self.memory.read(address+16*index,16)))
    def _set(self,address,index,value):self.memory.write(address+16*index,struct.pack('<2d',value.real,value.imag))
    def _vector(self,address,count):return [self._get(address,i)for i in range(count)]

    def begin(self,source,target):
        if self.pending is not None:raise ValueError('A cache transform is already pending')
        index=self.index(source,target)
        # The native call receives all three output pointers as arguments.
        # Keep those values even if a shared store aliases the pointer table.
        grid=self.address('xy',index);axis_x=self.address('x',index);axis_y=self.address('y',index)
        tx,ty,xy=table_storage(self.technology,self.frequency,source,target,samples_only=True)
        for x in range(self.nx+1):
            start=x*(self.nx+1)
            # Only the source's actual row is written; padding holes are not
            # zeroed. Rows past the allocation still address shared memory.
            self.memory.write(grid+16*start,complex_bytes(xy[start:start+self.ny+1]))
        self.pending=(grid,axis_x,axis_y,tx,ty)

    def transform(self,scratch_address):
        if self.pending is None:raise ValueError('No cache transform is pending')
        grid,axis_x,axis_y,tx,ty=self.pending;nx,ny=self.nx,self.ny;size=(nx+1)*(ny+1)
        self.memory.zero(scratch_address,32*nx)
        overlap=grid<scratch_address+32*max(nx,ny)and scratch_address<grid+16*size
        if ny<=nx and not overlap:
            # Scratch is disjoint and the final column overwrites its entire
            # declared extent. The existing batch preserves every operation.
            values=self._vector(grid,size);workspace=[]
            _transform_grid(values,nx,ny,observe_storage=workspace.extend)
            self.memory.write(grid,complex_bytes(values));self.memory.write(scratch_address,complex_bytes(workspace))
        else:
            # Literal copies retain aliases and scratch overflows on other
            # rectangular layouts, rather than extending the guest allocation.
            stride=ny+1
            for x in range(nx+1):
                for y in range(ny+1):self._set(scratch_address,y,self._get(grid,x*stride+y))
                for y in range(ny+1,2*ny):self._set(scratch_address,y,self._get(grid,x*stride+2*ny-y))
                values=self._vector(scratch_address,2*ny);_fft(values);self.memory.write(scratch_address,complex_bytes(values))
                for y in range(ny+1):self._set(grid,x*stride+y,self._get(scratch_address,y))
            for y in range(ny+1):
                for x in range(nx+1):self._set(scratch_address,x,self._get(grid,x*stride+y))
                for x in range(nx+1,2*nx):self._set(scratch_address,x,self._get(grid,(2*nx-x)*stride+y))
                values=self._vector(scratch_address,2*nx);_fft(values);self.memory.write(scratch_address,complex_bytes(values))
                for x in range(nx+1):self._set(grid,x*stride+y,self._get(scratch_address,x))

    def finish(self):
        # The native driver deletes grid scratch before constructing either
        # axis. The caller performs that free between transform and finish.
        grid,x,y,tx,ty=self.pending;nx,ny=self.nx,self.ny
        self.memory.write(x,complex_bytes(tx[:nx+1]));self.memory.write(y,complex_bytes(ty[:ny+1]))
        for i in range(nx,2*nx):self._set(x,i,self._get(x,2*nx-i))
        for i in range(ny,2*ny):self._set(y,i,self._get(y,2*ny-i))
        values=self._vector(x,2*nx);_fft(values);self.memory.write(x,complex_bytes(values))
        values=self._vector(y,2*ny);_fft(values);self.memory.write(y,complex_bytes(values));self.pending=None

    def input_file(self,path):
        candidates=[data for name,data in self.files if name==path]
        if len(candidates)!=1:raise ValueError('Missing or ambiguous native cache input file')
        return candidates[0]

    def load(self,path):
        """Read an already opened/validated file, selected by its actual path.

        The native filename rounds GHz to two decimals, and header validation
        does not compare frequency. Never select a file by header frequency.
        Path construction, header validation and failed/short IO are separate
        caller operations, not implemented by this successful-read component.
        """
        data=self.input_file(path);offset=16+40*len(self.technology.substrate)+236*self.metals
        for source in range(self.metals):
            for target in range(source,self.metals):
                index=self.index(source,target)
                for name in ('xy','x','y'):
                    size=self.inputs['arrays'][name]['size']
                    if len(data)<offset+size:raise ValueError('Truncated native cache table input')
                    self.memory.write(self.address(name,index),data[offset:offset+size]);offset+=size
        self.loaded=data

    def stream(self,mode):
        sizes=[4,4,8,40*len(self.technology.substrate),236*self.metals]
        sizes.extend(self.inputs['arrays'][name]['size']for i in range(self.metals*(self.metals+1)//2)for name in ('xy','x','y'))
        if mode=='warm':
            if self.loaded is None:raise ValueError('Cache input has not been loaded')
            chunks=[];offset=0
            for size in sizes:chunks.append((self.loaded[offset:offset+size],size));offset+=size
            if offset<len(self.loaded):chunks.append((self.loaded[offset:],len(self.loaded)-offset))
            return FileBytes(chunks,read_sizes=sizes)
        if mode!='cold':raise ValueError('Unknown disk-cache mode')
        header=struct.pack('<iid',self.nx,self.ny,self.frequency)
        raw=[bytes.fromhex(record)for record in self.inputs['technology']]
        chunks=[(header[:4],4),(header[4:8],4),(header[8:],8),(raw[0],len(raw[0])),(raw[1],len(raw[1]))]
        for i in range(self.metals*(self.metals+1)//2):
            for name in ('xy','x','y'):
                size=self.inputs['arrays'][name]['size'];chunks.append((self.memory.read(self.address(name,i),size),size))
        return FileBytes(chunks)

    def file_buffer(self,address,size,mode):
        function=write_buffer if mode=='cold'else read_buffer
        function(self.memory,address,size,self.stream(mode))
