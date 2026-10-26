"""Console log closure on the same heap, FILE list and thread state.

Order follows console_runtime.cpp / original 0x0804be20 and 0x0804c33c.
FILE stores share the glibc 2.39 narrow close translation (LGPL-2.1-or-later;
see web/GLIBC-LGPL-2.1.txt). Full caller/free/exit CPU ABI remains unfinished.
"""
from .libio_storage import close_byte_stream


class ProcessCleanup:
    def __init__(self,history,*,release,observe=None):
        self.history=history;self.heap=history.heap;self.memory=history.memory
        self.abi=history.libio
        self.tls=history.inputs.get('port_tail_abi',{}).get('tls_base',history.inputs.get('loader_context',{}).get('tls_base'))
        if self.tls is None:raise NotImplementedError('Log close requires the earlier thread ABI')
        self.release=release;self.observe=observe;self.calls=[]

    def point(self,phase,address=None):
        if self.observe is not None:self.observe(phase,self,address)

    def close(self,kind,address):
        m=self.memory
        # The preceding console writes normally flushed these streams.
        # A pending write must execute a real virtual write before resetting
        # its areas; it cannot silently disappear during semantic closure.
        def flush():
            mode=m.u32(address+104)
            if mode and mode<0x80000000:raise NotImplementedError('Wide log close needs its wide write path')
            if m.u32(address+20)!=m.u32(address+16):raise NotImplementedError('Log close with pending output needs its write path')
        self.calls.append(dict(kind=kind,file=address,free=[]));call=self.calls[-1]
        def release(pointer,caller):
            call['free'].append(pointer)
            self.release(pointer,caller,before_free=lambda:self.point('free',pointer))
        close_byte_stream(m,address,self.abi,tls_base=self.tls,release=release,flush=flush,
                          observe=lambda label:self.point('before')if label=='close_entry'else None)
        self.point('after')

    def close_logs(self):
        m=self.memory
        for kind,binding in(('log.input',0x80d7e24),('log.output',0x80d7e28)):
            self.close(kind,m.u32(binding))
        if m.read(0x80cbab8,1)!=b'\0':
            for kind,binding in(('recording.output',0x80d7e20),('recording.input',0x80d7e1c)):
                self.close(kind,m.u32(binding))
