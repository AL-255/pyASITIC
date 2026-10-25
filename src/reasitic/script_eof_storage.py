"""Resume the actual script stream after its nested port command returns.

The direct-script read loop follows command_session.cpp. Narrow fclose is
shared with the port-output continuation. No later native bytes or register
observations initialize the stream, allocator, FILE list or thread lock.
"""
from .libio_storage import close_byte_stream


class ScriptEOFStorage:
    def __init__(self,history,*,observe=None):
        self.history=history;self.heap=history.heap;self.memory=history.memory
        self.console=history.console;self.stream=history.script_stream
        self.buffer=self.memory.u32(self.stream.address+28)
        self.abi=history.libio;self.tls=history.inputs['port_tail_abi']['tls_base']
        self.events=[];self.freed=[];self.observe=observe;self.complete=False

    def point(self,label):
        if self.observe is not None:self.observe(label,self)

    def release(self,address,caller):
        m=self.memory;index=len(self.events)
        if address:
            word=m.u32(address-4);size=(word&~7)-(8 if word&2 else 4)
            self.freed.append(dict(event_index=index,address=address,size=size,data=m.read(address,size)))
        item=dict(kind='free',allocator='free',address=address,caller=caller)
        self.events.append(item);self.heap.free(address);item['returned']=True

    def run(self):
        self.point('script.read')
        line=self.history.inputs['workspace_address']+4160
        if self.stream.readline(line,300)is not None:
            raise NotImplementedError('Commands following the port export need the continuing outer dispatcher')
        self.point('script.eof')
        labels={'close_entry':'script.close','free.buffer':'script.free.buffer','free.file':'script.free.file'}
        close_byte_stream(self.memory,self.stream.address,self.abi,tls_base=self.tls,
                          release=self.release,observe=lambda label:self.point(labels[label]))
        self.point('script.return');self.complete=True
