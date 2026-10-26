"""Source exit-list traversal and ELF finalizer dependency ordering.

Follows glibc 2.39 stdlib/exit.c and elf/dl-fini.c, dl-call_fini.c,
dl-sort-maps.c, Copyright Free Software Foundation, Inc., LGPL-2.1-or-later;
see web/GLIBC-LGPL-2.1.txt. Addresses, layouts and lists are genuine earlier
process inputs. No later callback order, return or process outcome is loaded.
Individual ELF destructor bodies and full CPU/stack/FP ABI remain unfinished.
"""


class ExitStorage:
    def __init__(self,history,*,observe=None,release=None):
        self.history=history;self.m=history.memory;self.heap=history.heap
        self.inputs=history.inputs['exit_inputs'];self.ctx=history.inputs['loader_context']
        self.controls=self.inputs['controls'];self.fields=self.inputs['link_fields']
        self.tls=self.ctx['tls_base'];self.loader=self.ctx['loader_base'];self.libc=history.libio['libc_base']
        self.observe=observe;self.release=release;self.observe_crt=None;self.calls=[];self.orders=[];self.object_order=[]

    def control(self,name):return self.controls[name]['address']
    def field(self,map_,name):
        f=self.fields[name];value=int.from_bytes(self.m.read(map_+f['offset'],f['size']),'little')
        return(value>>f['bit'])&((1<<f['bits'])-1)if f['bits']else value
    def put_field(self,map_,name,value):
        f=self.fields[name];p=map_+f['offset']
        if f['bits']:
            old=int.from_bytes(self.m.read(p,f['size']),'little');mask=((1<<f['bits'])-1)<<f['bit'];value=(old&~mask)|((value<<f['bit'])&mask)
        self.m.write(p,(value&((1<<(8*f['size']))-1)).to_bytes(f['size'],'little'))
    def words(self,p):
        result=[]
        if p:
            while self.m.u32(p):result.append(self.m.u32(p));p+=4
        return result
    def deps(self,map_):return self.words(self.field(map_,'l_initfini'))
    def reldeps(self,map_):
        p=self.field(map_,'l_reldeps')
        return [self.m.u32(p+4+4*i)for i in range(self.m.u32(p))]if p else []
    def demangle(self,p):return(((p>>9)|(p<<23))&0xffffffff)^self.m.u32(self.tls+24)
    def counter(self):return int.from_bytes(self.m.read(self.control('__new_exitfn_called'),8),'little')

    def call(self,kind,pc,args,body):
        record=dict(kind=kind,pc=pc,arguments=list(args),index=len(self.calls));self.calls.append(record)
        if self.observe is not None:self.observe('before',self,record)
        body()
        record['returned']=True
        if self.observe is not None:self.observe('after',self,record)

    def sort_maps(self,maps,force_first,algorithm):
        if algorithm==0:
            first=maps[:int(force_first)];work=list(maps[int(force_first):]);n=len(work)
            if n<=1:return first+work
            seen=[0]*n;i=0
            while i<n:
                seen[i]=(seen[i]+1)&65535;this=work[i];move=None
                if this==self.field(this,'l_real')and self.field(this,'l_idx')!=0xffffffff:
                    for k in range(n-1,i,-1):
                        if this in self.deps(work[k]):move=k;break
                        if this in self.reldeps(work[k])and work[k]not in self.deps(this):move=k;break
                if move is not None:
                    work[i:move]=work[i+1:move+1];work[move]=this
                    if seen[i+1]>n-i:
                        i+=1;seen[i:]=[0]*(n-i)
                    else:
                        old=seen[i];seen[i:move]=seen[i+1:move+1];seen[move]=old
                    continue
                i+=1;seen[i:]=[0]*(n-i)
            return first+work
        if algorithm!=1:raise NotImplementedError('Unknown ELF finalizer sorting algorithm')
        for item in maps:self.put_field(item,'l_visited',0)
        rpo=[];used_reldeps=False
        def visit(item,relocations):
            nonlocal used_reldeps
            if self.field(item,'l_visited')or self.field(item,'l_faked'):return
            self.put_field(item,'l_visited',1)
            for dependency in self.deps(item):
                if not self.field(dependency,'l_visited')and not self.field(dependency,'l_main_map'):visit(dependency,relocations)
            if relocations and self.field(item,'l_reldeps'):
                used_reldeps=True
                for dependency in reversed(self.reldeps(item)):
                    if not self.field(dependency,'l_visited')and not self.field(dependency,'l_main_map'):visit(dependency,True)
            rpo.insert(0,item)
        for item in reversed(maps):
            visit(item,True)
            if len(rpo)==len(maps):break
        if len(rpo)!=len(maps):raise ValueError('ELF finalizer DFS did not cover its source map list')
        if used_reldeps:
            previous=rpo;rpo=[]
            for item in previous:self.put_field(item,'l_visited',0)
            for item in reversed(previous):
                visit(item,False)
                if len(rpo)==len(maps):break
        if force_first:
            index=rpo.index(maps[0]);rpo[1:index+1]=rpo[:index];rpo[0]=maps[0]
        return rpo

    def loader_fini(self):
        m=self.m;global_=self.control('_rtld_global');ro=self.control('_rtld_global_ro');fields=self.inputs['rtld_fields'];rof=self.inputs['rtld_ro_fields']
        def value(base,table,name):return m.u32(base+table[name]['offset'])
        if value(ro,rof,'_dl_naudit')or value(ro,rof,'_dl_debug_mask'):raise NotImplementedError('Audited/debug loader finalization needs its callback/output source')
        algorithm=value(ro,rof,'_dl_dso_sort_algo');nns=value(global_,fields,'_dl_nns')
        for ns in reversed(range(nns)):
            p=global_+fields['_dl_ns']['offset']+ns*self.inputs['namespace_size'];nf=self.inputs['namespace_fields'];count=value(p,nf,'_ns_nloaded');head=value(p,nf,'_ns_loaded')
            if not count or self.field(head,'l_auditing'):continue
            lock=global_+fields['_dl_load_lock']['offset'];tid=m.u32(self.control('thread_tid'))
            if m.u32(lock)or m.u32(lock+4)or m.u32(lock+8):raise NotImplementedError('Recursive/contended loader exit lock needs its source branch')
            if m.u32(lock+12)!=1:raise NotImplementedError('Alternate loader mutex type needs its source branch')
            for off,value_ in((0,1),(4,1),(8,tid),(16,m.u32(lock+16)+1)):m.put_u32(lock+off,value_)
            maps=[];cursor=head;seen=set()
            while cursor:
                if cursor in seen:raise ValueError('Cyclic source loader namespace')
                seen.add(cursor)
                if cursor==self.field(cursor,'l_real'):
                    self.put_field(cursor,'l_idx',len(maps));maps.append(cursor)
                    self.put_field(cursor,'l_direct_opencount',self.field(cursor,'l_direct_opencount')+1)
                cursor=self.field(cursor,'l_next')
            if (ns==0 and len(maps)!=count)or(ns and len(maps)not in(count,count-1)):raise ValueError('Loader namespace count differs from its source chain')
            order=self.sort_maps(maps,ns==0,algorithm);self.orders.append(dict(namespace=ns,maps=list(order)))
            for off,value_ in((4,0),(8,0),(16,m.u32(lock+16)-1),(0,0)):m.put_u32(lock+off,value_)
            self.object_order.extend(item for item in order if self.field(item,'l_init_called'))
            for item in order:
                if self.field(item,'l_init_called'):self.call('object',self.loader+0x1090,[item],lambda item=item:self.object_fini(item))
                self.put_field(item,'l_direct_opencount',self.field(item,'l_direct_opencount')-1)

    def object_fini(self,map_):
        m=self.m;self.put_field(map_,'l_init_called',0);base=m.u32(map_)
        array=m.u32(map_+32+4*26);length=m.u32(map_+32+4*28)
        if array:
            if not length or m.u32(length+4)%4:raise ValueError('Invalid ELF finalizer array size')
            start=base+m.u32(array+4)
            for index in reversed(range(m.u32(length+4)//4)):
                pc=m.u32(start+4*index);self.call('fini',pc,[],lambda pc=pc:self.fini_body(pc))
        old=m.u32(map_+32+4*13)
        if old:
            pc=base+m.u32(old+4);self.call('fini',pc,[],lambda:self.fini_body(pc))

    def fini_body(self,pc):
        if pc==0x80b4784 and'crt_inputs'in self.history.inputs:
            from .crt_storage import CRTStorage
            self.crt=CRTStorage(self,observe=self.observe_crt);return self.crt.main_fini()
        raise NotImplementedError(f'ELF finalizer body {pc:#x} requires its source implementation')

    def dispatch(self,pc,args):
        if pc!=self.loader+0x4e80:raise NotImplementedError(f'Registered exit callback {pc:#x} requires its source implementation')
        self.call('loader',pc,[],self.loader_fini)

    def handlers(self,status):
        m=self.m
        if m.u32(self.tls+12):raise NotImplementedError('Multithreaded exit needs its lock/wait paths')
        if m.u32(self.control('tls_dtor_list')):raise NotImplementedError('Thread-local destructor callbacks need their source implementation')
        lock=self.control('__exit_funcs_lock');head=self.control('__exit_funcs')
        if m.u32(lock):raise NotImplementedError('Contended exit-list lock needs its wait source')
        m.put_u32(lock,1)
        while m.u32(head):
            node=m.u32(head);restart=False
            if m.u32(node+4)>32:raise ValueError('Exit-list index exceeds its source structure')
            while m.u32(node+4):
                index=m.u32(node+4)-1;m.put_u32(node+4,index);f=node+8+16*index;flavor=m.u32(f);before=self.counter()
                if flavor in(0,1):continue
                if flavor not in(2,3,4):raise ValueError('Invalid source exit callback flavor')
                pc=self.demangle(m.u32(f+4));args=[]if flavor==3 else[m.u32(f+8),status]if flavor==4 else[status,m.u32(f+8)]
                if flavor==4:m.put_u32(f,0)
                m.put_u32(lock,0);self.call('registered',pc,args,lambda:self.dispatch(pc,args));m.put_u32(lock,1)
                if self.counter()!=before:restart=True;break
            if restart:continue
            following=m.u32(node);m.put_u32(head,following)
            if following:raise NotImplementedError('Dynamic exit-list node release needs its free caller ABI')
        m.write(self.control('__exit_funcs_done'),b'\1');m.put_u32(lock,0)
        raise NotImplementedError('Final stdio cleanup and exit_group still need their source implementation')

    def run(self,status):self.call('exit',self.libc+0x3ebd0,[status],lambda:self.handlers(status))
