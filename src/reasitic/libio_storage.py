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
    def __init__(self,memory,abi,*,errno_address=None):
        self.memory=memory;self.abi=abi;self.errno_address=errno_address
        if (abi['file']['size'],abi['plus']['size'],abi['lock_size'],abi['wide']['size'])!=(148,152,12,140):
            raise ValueError('FILE storage requires the i386 glibc 2.39 ABI')

    def _put(self,address,layout,name,value):
        field=self.abi[layout]['fields'][name];size=field['size']
        self.memory.write(address+field['offset'],(value&((1<<(8*size))-1)).to_bytes(size,'little'))

    def initialize(self,address,*,list_head=None):
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
        self._put(address,'file','_chain',self.abi['list_head']if list_head is None else list_head)
        self._put(address,'file','_fileno',-1)

    def failed_open(self,address,*,error_number=None):
        # Unlink clears _IO_LINKED, but does not clear the saved _chain.
        self._put(address,'file','_flags',MAGIC|CLOSED)
        if self.errno_address is not None:
            if error_number is None:raise ValueError('Failed open needs its earlier filesystem error')
            self.memory.put_u32(self.errno_address,error_number)

    def closed_byte_stream(self,address):
        # First narrow IO sets orientation to -1. Closing releases the buffer
        # then resets both areas and file flags; wide storage stays untouched.
        self._put(address,'file','_mode',-1)
        for field in POINTERS:self._put(address,'file',field,0)
        self._put(address,'file','_flags',MAGIC|CLOSED)
        self._put(address,'file','_fileno',-1);self._put(address,'file','_offset',-1)


def close_byte_stream(memory,address,abi,*,tls_base,release,observe=None,flush=None):
    """Successful narrow fclose on the live FILE, list and thread lock.

    release(address, caller) executes the caller's actual allocator. The
    observation hooks run before the original two free calls. Neither hook
    supplies state. Input streams have no output flush callback.
    """
    m=memory;fields=abi['file']['fields'];chain=fields['_chain']['offset']
    point=lambda label:None if observe is None else observe(label)
    point('close_entry')
    head=abi['libc_symbols']['_IO_list_all']['address'];following=m.u32(address+chain)
    if m.u32(head)==address:m.put_u32(head,following)
    else:
        previous=m.u32(head);seen=set()
        while previous and m.u32(previous+chain)!=address:
            if previous in seen:raise ValueError('FILE chain has a cycle')
            seen.add(previous);previous=m.u32(previous+chain)
        if not previous:raise ValueError('Closing FILE is absent from its continuing list')
        m.put_u32(previous+chain,following)
    m.put_u32(address,m.u32(address)&~0x80)
    lock=m.u32(address+fields['_lock']['offset']);locked=not bool(m.u32(address)&0x8000)
    if locked:
        if m.u32(tls_base+12):raise NotImplementedError('Multithreaded fclose requires its lock/wait path')
        thread=m.u32(tls_base+8);owner=m.u32(lock+8)
        if not owner:
            if m.u32(lock):raise NotImplementedError('Contended fclose requires its lock/wait path')
            m.put_u32(lock,1);m.put_u32(lock+8,thread)
        elif owner==thread:m.put_u32(lock+4,m.u32(lock+4)+1)
        else:raise NotImplementedError('Contended fclose requires its lock/wait path')
    if flush is not None:flush()
    buffer=m.u32(address+fields['_IO_buf_base']['offset'])
    point('free.buffer');release(buffer,abi['libc_base']+0x85439)
    FileStorage(m,abi).closed_byte_stream(address)
    if locked:
        depth=m.u32(lock+4)
        if depth:m.put_u32(lock+4,depth-1)
        else:m.put_u32(lock+8,0);m.put_u32(lock,0)
    point('free.file');release(address,abi['libc_base']+0x758ab)


def copy_cache_headers(memory,substrate_address,metal_address,header,substrates,metals):
    """The two fread destinations receive the external file's actual bytes.

    Raw name padding and unused fields come from the input file, which may
    have been written by another process. They are not reconstructed from the
    current technology or supplied from later native freed-array observations.
    """
    first=16;second=first+40*substrates;end=second+236*metals
    if len(header)<end:raise ValueError('Incomplete native cache header')
    memory.write(substrate_address,header[first:second]);memory.write(metal_address,header[second:end])
