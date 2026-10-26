"""Main ELF/CRT destructors and the pinned legacy unwind registry.

ASITIC reference: _fini 0x80b4784, __do_global_dtors_aux 0x804af20,
destroy_log_path_strings 0x804bdb0 and destroy_port_command_state 0x8060cb0;
inlined legacy string/member bodies 0x80b2240 and 0x80b3b40. Frame removal
follows the pinned libstdc++ 2.9 routine at +0x3084c. Source guest memory
supplies every cursor, callback, Rep, pool slot, registry link and binding.
No later destructor output or native return value initializes execution.
Full caller/lock/registry stack, GP and FP execution remain unfinished.
"""
from .legacy_strings import LegacyStrings
from .plt_fixup_storage import PltFixup


class CRTStrings(LegacyStrings):
    def __init__(self,crt):
        self.crt=crt
        super().__init__(crt.m,self.unused_allocate,self.release_rep,nil_address=0x80cf1a8,pool_address=0x80cf1c0)
    def unused_allocate(self,*args):raise NotImplementedError('Destructor string allocation needs its source branch')
    def release_rep(self,address,allocator):self.crt.release(address,self.crt.rep_caller)
    def put(self,address,size):
        if size>128:return super().put(address,size)
        self.crt.mutex(0x80cf20c,True,self.crt.main)
        super().put(address,size)
        self.crt.mutex(0x80cf20c,False,self.crt.main)


class CRTStorage:
    def __init__(self,exiting,*,observe=None):
        self.exiting=exiting;self.history=exiting.history;self.m=exiting.m;self.heap=exiting.heap
        self.inputs=self.history.inputs['crt_inputs'];self.ctx=exiting.ctx;self.observe=observe;self.calls=[]
        self.main=next(v for v in self.ctx['maps']if v['name']=='')
        self.legacy=next(v for v in self.ctx['maps']if v['address']==self.inputs['legacy_map'])
        if self.legacy['plt']['elf_sha256']!='bca97b602b1eec9f0b591bec0fa4dc5f84f1382636cc8f10094f1da8a3c77d34':raise NotImplementedError('CRT frame registry needs the pinned legacy ABI')
        self.legacy_base=self.m.u32(self.legacy['address']);self.loader=PltFixup(self.m,self.ctx['loader_base'],tls_base=exiting.tls);self.strings=CRTStrings(self)

    def call(self,kind,pc,args,body):
        record=dict(kind=kind,pc=pc,arguments=list(args),index=len(self.calls));self.calls.append(record)
        if self.observe is not None:self.observe('before',self,record)
        result=body();record.update(returned=True,value=result)
        if self.observe is not None:self.observe('after',self,record)
        return result

    def bind(self,map_,name):return self.loader.bind_value(map_['address'],name,map_['plt'])['target']
    def release(self,address,caller):
        if self.exiting.release is None:raise NotImplementedError('CRT free needs the continuing allocator caller')
        self.exiting.release(address,caller,before_free=lambda:None)

    def mutex(self,address,locking,map_):
        name=b'pthread_mutex_lock'if locking else b'pthread_mutex_unlock';pc=self.bind(map_,name)
        libc=self.exiting.libc;expected=libc+(0x90280 if locking else 0x91cf0)
        if pc!=expected:raise NotImplementedError(f'CRT mutex provider {pc:#x} needs its source implementation')
        def body():
            m=self.m
            if m.u32(self.exiting.tls+12):raise NotImplementedError('Multithreaded CRT mutex needs its wait paths')
            kind=m.u32(address+12)
            if kind not in(0,1):raise NotImplementedError('Alternate CRT mutex type needs its source branch')
            tid=m.u32(self.exiting.control('thread_tid'))
            if locking:
                if kind==1 and m.u32(address+8)==tid:
                    count=m.u32(address+4)
                    if count==0xffffffff:raise NotImplementedError('Recursive CRT mutex overflow needs its error return')
                    m.put_u32(address+4,count+1);return 0
                if m.u32(address)or m.u32(address+8):raise NotImplementedError('Contended CRT mutex needs its wait path')
                m.put_u32(address,1)
                if kind==1:m.put_u32(address+4,1)
                m.put_u32(address+8,tid);m.put_u32(address+16,m.u32(address+16)+1)
            else:
                if kind==1:
                    if m.u32(address+8)!=tid or not m.u32(address+4):raise NotImplementedError('Unowned recursive CRT mutex needs its error return')
                    count=m.u32(address+4)-1;m.put_u32(address+4,count)
                    if count:return 0
                m.put_u32(address+8,0);m.put_u32(address+16,m.u32(address+16)-1);m.put_u32(address,0)
            return 0
        return self.call('mutex.lock'if locking else'mutex.unlock',pc,[address],body)

    def members(self,address,charge,offsets,callers):
        for offset,caller in zip(offsets,callers):
            self.rep_caller=caller;self.strings.destroy(self.m.u32(address+offset))
        if charge&1:raise NotImplementedError('Deleting CRT global object needs its operator-delete caller')

    def callback(self,pc):
        if pc==0x804bdb0:
            def body():return self.call('logs.members',0x80b2240,[0x80d7e00,2],lambda:self.members(0x80d7e00,2,(24,20,16,12,8),(0x80b2273,0x80b22d5,0x80b2337,0x80b23a0,0x80b2402)))
            return self.call('logs.dtors',pc,[],body)
        if pc==0x8060cb0:
            def body():return self.call('port.member',0x80b3b40,[0x80d8660,2],lambda:self.members(0x80d8660,2,(116,),(0x80b3b73,)))
            return self.call('port.dtors',pc,[],body)
        raise NotImplementedError(f'CRT destructor callback {pc:#x} needs its source implementation')

    def deregister(self,begin):
        m=self.m;base=self.legacy_base;lock=base+0x351e0
        if m.u32(base+0x351dc):self.mutex(lock,True,self.legacy)
        link=base+0x4142c;seen=set()
        while m.u32(link):
            node=m.u32(link)
            if node in seen:raise ValueError('Cyclic source frame registry')
            seen.add(node)
            if m.u32(node+8)==begin:
                m.put_u32(link,m.u32(node+20))
                if m.u32(node):self.release(m.u32(node+12),base+0x308a1)
                if m.u32(base+0x351dc):self.mutex(lock,False,self.legacy)
                return node
            link=node+20
        if m.u32(base+0x351dc):self.mutex(lock,False,self.legacy)
        raise NotImplementedError('Frame deregistration of an absent object needs its abort path')

    def dtors(self):
        m=self.m
        if m.u32(0x80cb988):return
        while m.u32(m.u32(0x80cb984)):
            pointer=m.u32(0x80cb984);pc=m.u32(pointer);m.put_u32(0x80cb984,pointer+4);self.callback(pc)
        pc=self.bind(self.main,b'__deregister_frame_info')
        if pc!=self.legacy_base+0x3084c:raise NotImplementedError(f'CRT frame provider {pc:#x} needs its source implementation')
        self.call('frame.deregister',pc,[0x80d0560],lambda:self.deregister(0x80d0560));m.put_u32(0x80cb988,1)

    def main_fini(self):
        return self.call('main.fini',0x80b4784,[],lambda:self.call('main.dtors',0x804af20,[],self.dtors))
