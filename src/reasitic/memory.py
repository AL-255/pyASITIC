"""Sparse guest memory; unknown bytes are distinct from unmapped addresses.

This is a virtual byte store, not access to the browser or host address space.
Different matrix views and allocator metadata can refer to the same bytes.
"""
import struct


class MemoryFault(ValueError):
    def __init__(self,address,size):
        self.address,self.size=address,size
        super().__init__(f'Unmapped guest memory at {address:#x} ({size} bytes)')


class UnknownMemory(ValueError):
    def __init__(self,address,size):
        self.address,self.size=address,size
        super().__init__(f'Uninitialized guest memory at {address:#x} ({size} bytes)')


class Memory:
    """Mapped byte ranges with explicit initialization and shared aliases."""
    PAGE=4096

    def __init__(self,address_space):
        self.address_space=address_space;self._pages={}

    def _check(self,address,size):
        if isinstance(address,bool)or not isinstance(address,int)or isinstance(size,bool)or not isinstance(size,int)or size<0:
            raise ValueError('Guest memory ranges require integer addresses and nonnegative sizes')
        if not 0<=address<=0xffffffff or address+size>0x100000000 or not self.address_space.contains(address,size):
            raise MemoryFault(address,size)

    def read(self,address,size):
        self._check(address,size);result=bytearray();end=address+size
        while address<end:
            page,offset=divmod(address,self.PAGE);count=min(end-address,self.PAGE-offset)
            data,known=self._pages.get(page,(None,None))
            if known is None or 0 in known[offset:offset+count]:raise UnknownMemory(address,count)
            result.extend(data[offset:offset+count]);address+=count
        return bytes(result)

    def write(self,address,data):
        data=bytes(data);self._check(address,len(data));start=0
        while start<len(data):
            page,offset=divmod(address,self.PAGE);count=min(len(data)-start,self.PAGE-offset)
            if page not in self._pages:self._pages[page]=(bytearray(self.PAGE),bytearray(self.PAGE))
            contents,known=self._pages[page]
            contents[offset:offset+count]=data[start:start+count];known[offset:offset+count]=b'\1'*count
            start+=count;address+=count

    def forget(self,address,size):
        """Forget released storage, even after its mapping has been removed."""
        end=address+size
        while address<end:
            page,offset=divmod(address,self.PAGE);count=min(end-address,self.PAGE-offset)
            if page in self._pages:
                self._pages[page][1][offset:offset+count]=b'\0'*count
                if not any(self._pages[page][1]):del self._pages[page]
            address+=count

    def write_unknown(self,address,size):
        """Store an unknown source value, retaining normal mapping checks."""
        self._check(address,size);self.forget(address,size)

    def zero(self,address,size):self.write(address,b'\0'*size)
    def u32(self,address):return struct.unpack('<I',self.read(address,4))[0]
    def put_u32(self,address,value):self.write(address,struct.pack('<I',value&0xffffffff))
    def u16(self,address):return struct.unpack('<H',self.read(address,2))[0]
    def put_u16(self,address,value):self.write(address,struct.pack('<H',value))


class ComplexView:
    """The original column-major 16-byte complex matrix addressing rule.

    Indices are intentionally not bounded by the declared matrix dimensions:
    native via stamps can alias other mapped objects. Mapping and initialization
    checks still apply to every load/store.
    """
    def __init__(self,memory,address,size,stride=None):
        self.memory,self.address,self.size=memory,address,size
        self.stride=size if stride is None else stride

    def cell_address(self,row,column):return self.address+16*(column*self.stride+row)
    def get(self,row,column):return complex(*struct.unpack('<2d',self.memory.read(self.cell_address(row,column),16)))
    def set(self,row,column,value):self.memory.write(self.cell_address(row,column),struct.pack('<2d',value.real,value.imag))
    def write(self,matrix):
        """Store a complete square matrix in native column-major order."""
        if len(matrix)!=self.size or any(len(row)!=self.size for row in matrix):
            raise ValueError('Guest matrix dimensions must match its view')
        for column in range(self.size):
            for row in range(self.size):self.set(row,column,matrix[row][column])
