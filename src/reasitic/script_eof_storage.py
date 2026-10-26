"""Resume the actual script stream after its nested port command returns.

The direct-script read loop follows command_session.cpp. Narrow fclose is
shared with the port-output continuation. No later native bytes or register
observations initialize the stream, allocator, FILE list or thread lock.
"""
from .libio_storage import close_byte_stream
from .memory import UnknownMemory


class ScriptEOFStorage:
    def __init__(self,history,*,observe=None,observe_malloc=None,observe_cleanup=None,observe_exit=None):
        self.history=history;self.heap=history.heap;self.memory=history.memory
        self.console=history.console;self.stream=history.script_stream
        self.buffer=self.memory.u32(self.stream.address+28)
        self.abi=history.libio;self.tls=history.inputs['port_tail_abi']['tls_base']
        self.events=[];self.freed=[];self.observe=observe;self.complete=False
        self.io_calls=[];self.io_pending=[]
        self.malloc_calls=[];self.observe_malloc=observe_malloc
        self.observe_cleanup=observe_cleanup
        self.observe_exit=observe_exit

    def point(self,label):
        if label=='script.free.file':self.return_abi=self.history._script_return_abi(self.stream.address)
        if self.observe is not None:self.observe(label,self)

    def release(self,address,caller,*,before_free=None):
        m=self.memory;index=len(self.events)
        if address:
            word=m.u32(address-4);size=(word&~7)-(8 if word&2 else 4)
            self.freed.append(dict(event_index=index,address=address,size=size,data=m.read(address,size)))
        item=dict(kind='free',allocator='free',address=address,caller=caller)
        self.events.append(item)
        if before_free is not None:before_free()
        self.heap.free(address);item['returned']=True

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

    def allocate(self,name,size,allocator='malloc'):
        item=dict(kind='allocate',allocator=allocator,request=size,caller=self.abi['libc_base']+0x75523)
        self.events.append(item);address=self.heap.malloc(size);item.update(address=address,returned=True);return address

    def release_named(self,name,address,allocator='malloc'):
        if allocator!='array':raise NotImplementedError('Additional REPL allocator interfaces need their call ABI')
        if not address:return
        ctx=self.history.inputs['loader_context']
        legacy=next(item for item in ctx['maps']if item['name'].endswith('/libstdc++-libc6.1-1.so.2'))
        if legacy['plt']['elf_sha256']!='bca97b602b1eec9f0b591bec0fa4dc5f84f1382636cc8f10094f1da8a3c77d34':raise NotImplementedError('Cache delete[] needs the pinned legacy ABI')
        before=len(self.events);self.release(address,self.memory.u32(legacy['address'])+0x30d4e);self.events[before]['allocator']='array'

    def resume_repl(self):
        if not self.complete:raise ValueError('The source script must return before entering the REPL')
        def cleanup_observe(phase,cleanup,address):
            if self.observe_cleanup is not None:self.observe_cleanup(phase,cleanup,address,self)
        def exit_observe(phase,engine,record):
            if self.observe_exit is not None:self.observe_exit(phase,engine,record,self)
        self.history._after_script_close(self.return_abi,allocate=self.allocate,release=self.release_named,
                                        point=lambda kind:self.point('interactive.parse'if kind=='parse'else kind),observe_io=self.observe_io,
                                        release_cleanup=self.release,observe_cleanup=cleanup_observe,observe_exit=exit_observe)

    def observe_io(self,phase,kind,registers,positions):
        if kind=='malloc':
            if phase=='before':self.malloc_calls.append({})
            self.malloc_calls[-1][phase]=dict(registers)
            if self.observe_malloc is not None:self.observe_malloc(phase,registers,self)
            return
        m=self.memory;stdin=self.history.inputs['stdin_stream']['address'];s=registers['esp']
        if phase=='before':
            if m.u32(s+(12 if kind=='fgets'else 4))!=(0 if kind=='llseek'else stdin):return
            item=dict(kind=kind);self.io_calls.append(item);self.io_pending.append(item)
        else:
            if not self.io_pending:return
            item=self.io_pending[-1]
            if item['kind']!=kind or item['before']['registers']['esp']+4!=s:return
            self.io_pending.pop()
        workspace=self.history.inputs['workspace_address']
        stack=next(r for r in self.history.inputs['initial_regions']if r['address']<=workspace and workspace+4460<=r['address']+len(r['data'])//2)
        def region(address,size):
            try:return dict(address=address,size=size,data=m.read(address,size))
            except UnknownMemory:
                words=[]
                for offset in range(0,size,4):
                    try:word=m.read(address+offset,min(4,size-offset))
                    except UnknownMemory:word=None
                    words.append(word)
                return dict(address=address,size=size,data=None,words=words)
        item[phase]=dict(registers=dict(registers),stdin_position=positions[0],regions=[region(stack['address'],len(stack['data'])//2),region(stdin,152)])
