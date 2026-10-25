"""Source S-record output and narrow fclose on the continuing port stream.

The record follows two_port_output.cpp. Decimal fields use the translated
glibc formatter. Close stores follow glibc 2.39 libio/iofclose.c, genops.c and
fileops.c (LGPL-2.1-or-later; see web/GLIBC-LGPL-2.1.txt). Earlier stream/ABI
bindings and live guest ports are inputs; no later observation is loaded.
"""
import struct
from .node_storage import PORT_ADDRESSES
from .network_metrics import _scattering
from .printf_float_digits import format_binary64
from .retained_scalar import Real as R
from .libio_storage import FileStorage

SCATTERING_ADDRESSES=dict(s11=0x80d8d58,s12=0x80d8d28,s21=0x80d8d48,s22=0x80d8d18)
RECTANGULAR=b'\n'+b'  '.join([b'%-20.15e']*9)


class PortOutputStorage:
    def __init__(self,history,*,observe=None):
        self.heap=history.heap;self.memory=history.memory;self.console=history.console
        self.stream=history.port_stream;self.name=history.port_name;self.abi=history.libio
        self.tls=history.inputs['port_tail_abi']['tls_base']
        self.events=[];self.freed=[];self.printf_calls=[];self.observe=observe

    def point(self,label):
        if self.observe is not None:self.observe(label,self)

    def release(self,address,caller):
        m=self.memory;index=len(self.events);word=m.u32(address-4);size=(word&~7)-(8 if word&2 else 4)
        self.freed.append(dict(event_index=index,address=address,size=size,data=m.read(address,size)))
        self.events.append(dict(kind='free',allocator='free',address=address,caller=caller));self.heap.free(address);self.events[-1]['returned']=True

    def record(self,frequency):
        m=self.memory
        if m.u32(0x80d86cc)!=1 or m.read(0x80d86d0,1)!=b'\0':raise NotImplementedError('Additional port formats need their source output paths')
        self.point('record_entry')
        y={name:complex(*struct.unpack('<2d',m.read(address,16)))for name,address in PORT_ADDRESSES.items()}
        values=_scattering(y);cells=dict(s11=values[0][0],s12=values[0][1],s21=values[1][0],s22=values[1][1])
        for name in('s11','s22','s21','s12'):
            z=cells[name];m.write(SCATTERING_ADDRESSES[name],struct.pack('<2d',z.real,z.imag))
        arguments=struct.pack('<d',float(R(frequency)*float.fromhex('0x1.12e0be826d695p-30')))
        arguments+=b''.join(m.read(SCATTERING_ADDRESSES[name],16)for name in('s11','s21','s12','s22'))
        self.printf_calls.append(dict(file=self.stream.address,format=RECTANGULAR,arguments=arguments,caller=0x8088f8d,events=len(self.events)))
        fields=[format_binary64(struct.unpack_from('<Q',arguments,offset)[0],'e',15,20,'-')for offset in range(0,len(arguments),8)]
        self.stream.write(b'\n'+b'  '.join(fields));self.point('record_return')

    def close(self):
        m=self.memory;file=self.stream.address;fields=self.abi['file']['fields'];chain=fields['_chain']['offset']
        self.point('close_entry')
        # fclose unlinks before close_it flushes and releases the buffer.
        head=self.abi['libc_symbols']['_IO_list_all']['address'];following=m.u32(file+chain)
        if m.u32(head)==file:m.put_u32(head,following)
        else:
            previous=m.u32(head);seen=set()
            while previous and m.u32(previous+chain)!=file:
                if previous in seen:raise ValueError('FILE chain has a cycle')
                seen.add(previous);previous=m.u32(previous+chain)
            if not previous:raise ValueError('Port FILE is absent from its continuing list')
            m.put_u32(previous+chain,following)
        m.put_u32(file,m.u32(file)&~0x80)
        lock=m.u32(file+fields['_lock']['offset']);locked=not bool(m.u32(file)&0x8000)
        if locked:
            if m.u32(self.tls+12):raise NotImplementedError('Multithreaded fclose requires its lock/wait path')
            thread=m.u32(self.tls+8);owner=m.u32(lock+8)
            if not owner:
                if m.u32(lock):raise NotImplementedError('Contended fclose requires its lock/wait path')
                m.put_u32(lock,1);m.put_u32(lock+8,thread)
            elif owner==thread:m.put_u32(lock+4,m.u32(lock+4)+1)
            else:raise NotImplementedError('Contended fclose requires its lock/wait path')
        self.stream.flush();self.point('free.buffer')
        self.release(self.stream.buffer,self.abi['libc_base']+0x85439)
        FileStorage(m,self.abi).closed_byte_stream(file)
        if locked:
            depth=m.u32(lock+4)
            if depth:m.put_u32(lock+4,depth-1)
            else:m.put_u32(lock+8,0);m.put_u32(lock,0)
        self.point('free.file')
        self.release(file,self.abi['libc_base']+0x758ab);self.point('export_return')

    def run(self):
        m=self.memory;first,last,step=(struct.unpack('<d',m.read(address,8))[0]for address in(0x80d86a0,0x80d86a8,0x80d86b0))
        self.record(first)
        if R(first)+step<=R(last):raise NotImplementedError('The next frequency requires another continuing driver solve')
        self.close()
