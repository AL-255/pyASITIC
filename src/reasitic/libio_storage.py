"""i386 glibc 2.39 narrow FILE construction and successful close stores.

Follows libio/iofopen.c, genops.c, fileops.c and iofclose.c, Copyright (C)
1993-2024 Free Software Foundation, Inc., LGPL-2.1-or-later. See the shipped
web/GLIBC-LGPL-2.1.txt. Distributed without warranty of merchantability or
fitness for a particular purpose. Python translation Copyright (C) 2026
pyASITIC authors. ABI layouts, loader symbol addresses and the prior stream
head are caller inputs. Uninitialized fields and padding are preserved.
"""

POINTERS=('_IO_read_ptr','_IO_read_end','_IO_read_base','_IO_write_base',
          '_IO_write_ptr','_IO_write_end','_IO_buf_base','_IO_buf_end',
          '_IO_save_base','_IO_backup_base','_IO_save_end')
MAGIC=0xfbad0000
CLOSED=0x2000|4|8|0x400


class FileStorage:
    def __init__(self,memory,abi):
        self.memory=memory;self.abi=abi
        if (abi['file']['size'],abi['plus']['size'],abi['lock_size'],abi['wide']['size'])!=(148,152,12,140):
            raise ValueError('FILE storage requires the i386 glibc 2.39 ABI')

    def _put(self,address,layout,name,value):
        field=self.abi[layout]['fields'][name];size=field['size']
        self.memory.write(address+field['offset'],(value&((1<<(8*size))-1)).to_bytes(size,'little'))

    def initialize(self,address):
        m=self.memory;plus=self.abi['plus']['size'];wide=address+plus+self.abi['lock_size']
        self._put(address,'file','_lock',address+plus)
        self._put(address,'file','_flags',MAGIC)
        self._put(address,'file','_flags2',128 if self.abi['needs_locking']else 0)
        for field in (*POINTERS,'_chain','_markers','_cur_column','_vtable_offset'):self._put(address,'file',field,0)
        m.zero(address+plus,self.abi['lock_size'])
        self._put(address,'file','_mode',0);self._put(address,'file','_wide_data',wide)
        for field in POINTERS:self._put(wide,'wide',field,0)
        self._put(wide,'wide','_wide_vtable',self.abi['wide_jumps'])
        self._put(address,'file','_freeres_list',0)
        self._put(address,'plus','vtable',self.abi['file_jumps'])
        self._put(address,'file','_offset',-1)
        self._put(address,'file','_flags',MAGIC|CLOSED|0x80)
        self._put(address,'file','_chain',self.abi['list_head'])
        self._put(address,'file','_fileno',-1)

    def failed_open(self,address):
        # Unlink clears _IO_LINKED, but does not clear the saved _chain.
        self._put(address,'file','_flags',MAGIC|CLOSED)

    def closed_byte_stream(self,address):
        # First narrow IO sets orientation to -1. Closing releases the buffer
        # then resets both areas and file flags; wide storage stays untouched.
        self._put(address,'file','_mode',-1)
        for field in POINTERS:self._put(address,'file',field,0)
        self._put(address,'file','_flags',MAGIC|CLOSED)
        self._put(address,'file','_fileno',-1);self._put(address,'file','_offset',-1)


def copy_cache_headers(memory,substrate_address,metal_address,header,substrates,metals):
    """The two fread destinations receive the external file's actual bytes.

    Raw name padding and unused fields come from the input file, which may
    have been written by another process. They are not reconstructed from the
    current technology or supplied from later native freed-array observations.
    """
    first=16;second=first+40*substrates;end=second+236*metals
    if len(header)<end:raise ValueError('Incomplete native cache header')
    memory.write(substrate_address,header[first:second]);memory.write(metal_address,header[second:end])
