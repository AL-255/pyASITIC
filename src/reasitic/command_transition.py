"""Source direct-script/port preparation on the continuing process memory.

The glibc fatal-message mapping follows libc_fatal.c, LGPL-2.1-or-later;
see web/GLIBC-LGPL-2.1.txt. No host process is signaled.
"""
import struct
from .command_storage import Characters,CommandStorage,ScanHistory,string
from .geometry_storage import GeometryStorage
from .legacy_strings import LegacyStrings
from .libio_storage import FileStorage
from .stdio_storage import InputStream,OutputStream
from .port_header_storage import NativePortStack,calendar,header
from .heap import HeapCorruption
from .signal_install_storage import install_console_signals
from .plt_fixup_storage import PltFixup
from .dispatch_storage import DispatchStorage,enter_dispatch
from .poll_storage import poll_select,select64_entry
from .select_storage import select64_dispatch,select_syscall_entry
from .kill_storage import kill_vdso_entry,vdso_kernel_entry
from .parser_callers import ParserCallers
from .repl_storage import ReplStorage
from .stdin_storage import StdinStorage


class CommandTransition:
    def __init__(self,heap,memory,console,inputs,*,head,strings,libio,technology,cells,script,cache_arrays):
        self.heap=heap;self.memory=memory;self.console=console;self.inputs=inputs;self.libio=libio
        self.technology=technology;self.cells=cells;self.script=script;self.events=[];self.freed=[];self.files=[];self.calendar_calls=[];self.result=None;self.points=[]
        self.cache_arrays=cache_arrays;self.printf_calls=[]
        self.stdin_position=inputs['stdin_stream'].get('file_position',0)
        self.geometry=GeometryStorage(heap,memory,head)
        self.strings=LegacyStrings(memory,lambda size,allocator:self.allocate('filename',size,allocator),lambda address,allocator:self.release('filename',address,allocator),nil_address=strings['nil_address'],pool_address=strings['pool_address'])
        self.characters=Characters(inputs['character_tables'])
        self.parser=CommandStorage(memory,self.characters,self.find_shape,console.warning)
        self.stack=NativePortStack(memory,inputs['registers']['ebp'])

    def allocate(self,name,size,allocator='malloc'):
        item=dict(kind='allocate',name=name,request=size,allocator=allocator);self.events.append(item)
        address=self.heap.malloc(size);item.update(address=address,returned=True);return address

    def release(self,name,address,allocator='malloc'):
        item=dict(kind='free',name=name,address=address,allocator=allocator);index=len(self.events);self.events.append(item)
        if address:
            word=self.memory.u32(address-4);size=(word&~7)-(8 if word&2 else 4)
            self.freed.append(dict(event_index=index,address=address,size=size,data=self.memory.read(address,size)))
        try:self.heap.free(address)
        except HeapCorruption as error:
            # glibc libc_fatal.c maps an abort-message page independently of
            # malloc's mmap accounting, then raises SIGABRT. Model the virtual
            # mapping/message; never signal the host process or browser.
            text=str(error).encode()+b'\n\0';size=(len(text)+4095)&~4095
            abort=self.heap.address_space.map(size);self.memory.zero(abort,size)
            self.memory.put_u32(abort,size);self.memory.write(abort+4,text)
            raise
        item['returned']=True

    def find_shape(self,name):
        return next((address for address in self.geometry.shapes()if self.geometry.text(address)==name),None)

    def _timezone(self,timestamp):
        data=self.inputs['timezone'];environment=data['environment'];old=self.memory.u32(data['old_tz_global'])
        value=environment.encode()if environment is not None else None
        if value==b'':value=b'Universal'
        if value is not None and value.startswith(b':'):value=value[1:]
        if value is None or not old or string(self.memory,old)!=value:
            if value is not None:raise NotImplementedError('Changed explicit TZ environment requires the source timezone parser')
            value=b'/etc/localtime';self.release('timezone.old',old)
            pointer=self.allocate('timezone.name',len(value)+1);self.memory.write(pointer,value+b'\0');self.memory.put_u32(data['old_tz_global'],pointer)
            # tzfile.c's unchanged absolute-file path frees its null temporary.
            self.release('timezone.path',0)
        return calendar(timestamp,bytes.fromhex(data['tzfile']))

    def _port(self,identity,records):
        m=self.memory;count=m.u32(records+256);arg=lambda index:records+260*(index+1)
        value=lambda index:struct.unpack('<f',m.read(arg(index)+256,4))[0]
        transformer=identity==524;index=2 if transformer else 1
        first=last=step=value(index)
        if count>(4 if transformer else 3):first,last,step=value(index),value(index+1),value(index+2)
        if last<first:
            if transformer:last=first
            else:first,last=last,first
        if step<1e-10:step=first
        for address,number in ((0x80d86a0,first),(0x80d86a8,last),(0x80d86b0,step)):m.write(address,struct.pack('<d',number))
        fmt_index=5 if transformer else 4;parameter=1
        if count>fmt_index:
            self.characters.normalize(m,arg(fmt_index),0xae)
            if string(m,arg(fmt_index))!=b'S':raise NotImplementedError('Additional port parameter headers are not implemented')
        m.put_u32(0x80d86cc,parameter)
        if not transformer:m.write(0x80d86d0,b'\1');m.write(0x80d86c8,b'\1')
        if count>fmt_index+1:
            self.characters.normalize(m,arg(fmt_index+1),0xae);text=string(m,arg(fmt_index+1))
            if text not in (b'RECT',b'SQUARE',b'REIM',b'XY'):raise NotImplementedError('Additional port representation headers are not implemented')
            m.write(0x80d86d0,b'\0')
        if not transformer and count>6:
            self.characters.normalize(m,arg(6),32);mode=string(m,arg(6))
            if b'SLOW'in mode:m.write(0x80d86c8,b'\0')
            elif b'FAST'not in mode:self.console.warning('Warning:  Cannot understand 6th argument, defaulting to FAST.')
        filename=m.u32(0x80d86d4)
        if count>7:
            source=arg(7);text=string(m,source);filename=self.strings.replace(filename,0,0xffffffff,text)
            m.put_u32(0x80d86d4,filename);self.stack.filename_copy(source,filename,len(text))
        name=self.strings.c_string(filename)
        first_shape=m.u32(arg(0)+256);second_shape=m.u32(arg(1)+256)if transformer else first_shape
        list_head=self.libio['libc_symbols']['_IO_list_all']['address']
        file=self.allocate('port.file',304);file_storage=FileStorage(m,self.libio)
        file_storage.initialize(file,list_head=m.u32(list_head));m.put_u32(list_head,file)
        self.point('header')
        buffer=self.allocate('port.buffer',4096)
        layout=self.libio['file']['fields'];script_fd=struct.unpack_from('<i',bytes.fromhex(self.inputs['script_stream']['data']),layout['_fileno']['offset'])[0]
        stream=OutputStream(m,file,buffer,4096,self.libio,script_fd+1)
        stamp_address,stamp=self.stack.timestamp(identity)
        prefix=b'\n!*************************************************************************\n!! ASITIC Ver 10.20.99.0.0.0\n!!  Data generated by the <'+(b'2PortTrans'if transformer else b'2Port')+b'> command in <slow> mode.'
        stream.write(prefix)
        calendar_event=len(self.events)
        date=self._timezone(stamp);self.calendar_calls.append(dict(address=stamp_address,data=struct.pack('<i',stamp).hex(),text=date.hex(),events=calendar_event))
        data=header(first_shape,m,self.technology,bytes.fromhex(self.console.inputs['technology_name']),bytes.fromhex(self.console.inputs['directory']),self.cells,date,transformer=transformer)
        if not data.startswith(prefix):raise ValueError('Source port header prefix differs from its first writes')
        stream.write(data[len(prefix):]);stream.flush()
        self.files.append(dict(name=name,data=bytes(stream.data),address=file,buffer=buffer))
        if not transformer:
            kind=m.u32(first_shape+0x50)
            if kind not in (0,1,16,17,18,4):self.console.warning('Warning:  User defined structure type may not be compatible with 2port command.')
            if kind==4:raise NotImplementedError('Capacitor analysis after port setup is not bound')
            if m.read(0x80d86c8,1)!=b'\0':raise NotImplementedError('Analytical port dispatch is not bound')
        self.result=dict(driver='calctrans'if transformer else'pi2',arguments=[first_shape,second_shape,first_shape]if transformer else[first_shape,first_shape])

    def run(self):
        m=self.memory;inputs=self.inputs;records=inputs['workspace_address'];line=records+4160
        raw=bytes.fromhex(inputs['script_stream']['data']);base,end=struct.unpack_from('<I',raw,28)[0],struct.unpack_from('<I',raw,8)[0]
        if end-base!=len(self.script):raise NotImplementedError('Script initial external-file offset needs its earlier descriptor position')
        source=InputStream(m,inputs['script_stream']['address'],self.script,end-base,self.allocate)
        histories=[ScanHistory(None,None,None)for _ in range(15)]
        while source.readline(line,300)is not None:
            self.console.warning(string(m,line));self.characters.normalize(m,line,2)
            if m.read(line,1)==b'#':continue
            self.point('parse')
            identity=self.parser.parse(line,records,histories)
            if identity in (528,524):self._port(identity,records);return
            if identity==-2:self.console.warning('Unknown or Mistyped Commnd')
            elif identity!=-3:raise NotImplementedError('Additional direct-script command transition is not bound')
        self._script_eof(source)

    def _script_eof(self,source):
        m=self.memory;address=source.address;abi=self.libio;layout=abi['file']['fields'];head=abi['libc_symbols']['_IO_list_all']['address']
        pointer=m.u32(head);previous=None
        while pointer!=address:
            if not pointer:raise ValueError('Source closing script FILE is absent from stream chain')
            previous=pointer;pointer=m.u32(pointer+layout['_chain']['offset'])
        following=m.u32(address+layout['_chain']['offset'])
        if previous is None:m.put_u32(head,following)
        else:m.put_u32(previous+layout['_chain']['offset'],following)
        buffer=m.u32(address+28);FileStorage(m,abi).closed_byte_stream(address)
        self.release('script.buffer',buffer)
        loader_context=self.inputs.get('loader_context');stdio=self.inputs.get('stdio_context');incoming=None;loader=None
        if loader_context:
            size=m.u32(address-4)&~7
            if not self.heap._cache_has_space(size):raise NotImplementedError('Closing FILE without a tcache return needs its volatile-register path')
            index=self.heap._cache_index(size)
            libc_bases={s['address']-s['offset']for s in abi['libc_symbols'].values()}
            if len(libc_bases)!=1:raise ValueError('Inconsistent earlier libc bindings')
            libc_base=libc_bases.pop()
            # __libc_free restores errno through its TLS offset in ECX;
            # successful tcache insertion leaves the size-class index in EDX.
            # fclose returns its saved success status in EAX. No later PLT
            # entry observation supplies any of these incoming registers.
            incoming=dict(eax=0,ecx=m.u32(libc_base+0x22fe34+0xa0),edx=index)
            if stdio:incoming.update((key,stdio['registers'][key])for key in ('cs','ss','ds','es','fs','gs','orig_eax'))
            loader=PltFixup(m,loader_context['loader_base'],tls_base=loader_context['tls_base'])
        self.release('script.file',address)
        if self.inputs['repl']['history_enabled']:raise NotImplementedError('Readline signal installation needs its initial action state')
        bases={symbol['address']-symbol['offset']for symbol in abi['libc_symbols'].values()}
        if len(bases)!=1:raise ValueError('Inconsistent earlier libc symbol bindings')
        installed=install_console_signals(m,self.inputs['workspace_address'],bases.pop(),loader=loader,loader_context=loader_context,incoming=incoming)
        repl_storage=None;input_storage=None
        if stdio:
            m.write(0x80cbab0,b'\0');m.put_u32(0x80cbab4,0);m.write(0x80cba60,b'\0')
        flush_abi=bool(stdio and stdio.get('flush_abi'))
        printf_abi=bool(stdio and stdio.get('printf_abi'))
        if printf_abi:self.console.record('message',string(m,0x80b4821),False)
        else:self.console.emit('message',b'ASITIC>  ',False,flush=not flush_abi)
        if stdio:
            repl_storage=ReplStorage(m,stdio,libc_base=libc_base,tls_base=loader_context['tls_base'],loader=loader,loader_context=loader_context,heap=self.heap)
            self.printf_calls=repl_storage.printf_calls
            registers=repl_storage.before_poll(installed['main_registers'],installed['line'])
            registers=poll_select(m,registers,loader,loader_context)
            registers=select64_entry(m,registers,libc_base=libc_base,tls_base=loader_context['tls_base'],sar31_af=stdio['sar31_af'])
            registers=select64_dispatch(m,registers,libc_base=libc_base,tls_base=loader_context['tls_base'])
            select_syscall_entry(m,registers,libc_base=libc_base,tls_base=loader_context['tls_base'])
            # The external input is the launcher's regular answers file.
            # Kernel timeout copyback and the child IO frames remain missing
            # source work; every later byte remains in the strict comparison.
            registers=repl_storage.before_input(orient=not stdio.get('input_abi'))
            if stdio.get('input_abi'):
                input_storage=StdinStorage(m,loader,loader_context,stdio['input_abi'],libc_base=libc_base,tls_base=loader_context['tls_base'],heap=self.heap)
                input_storage.enter(registers)
        stdin=self.inputs['stdin_stream'];raw=bytes.fromhex(stdin['data']);base,end=struct.unpack_from('<I',raw,28)[0],struct.unpack_from('<I',raw,8)[0]
        if base:raise NotImplementedError('Earlier buffered interactive input offset is not yet bound')
        if input_storage and input_storage.profile.get('read_abi')and'file_position'not in stdin:
            raise ValueError('Read ABI needs the earlier descriptor position')
        source=InputStream(m,stdin['address'],bytes.fromhex(stdin['file_data']),self.stdin_position,self.allocate)
        # execute_command_script's 0x116c-byte frame has returned. main's
        # input line is EBP-0x400; dispatch_command_line subsequently reserves
        # its own 0x1040-byte command records. Both reuse the original stack.
        script_frame=self.inputs['workspace_address']+4460
        line=installed['line']
        read=source.readline(line,1024,abi=input_storage)
        self.stdin_position=source.position
        if read is None:raise NotImplementedError('Interactive EOF shutdown requires its own source path')
        # repl_read_stdio appends a newline even when fgets already retained
        # the input newline. finish() logs those bytes before normalization.
        if input_storage:
            registers=input_storage.returned(len(read));registers=input_storage.append_newline(registers,repl_storage.frame);text=string(m,line)
        else:text=string(m,line)+b'\n';m.write(line,text+b'\0')
        repl=self.inputs['repl'];history=repl['history_enabled']
        if not printf_abi:self.console.write_stream(repl['input_log'],text+(b'\n'if history else b''),flush=not flush_abi)
        output_log=self.console.inputs['streams']['log']['address']
        def write_output():self.console.write_stream(output_log,b'ASITIC>  '+text+(b'\n\n'if history else b''),flush=not flush_abi)
        if flush_abi:repl_storage.finish_line(self.characters,repl['input_log'],output_log,write_output=None if printf_abi else write_output,incoming=registers if printf_abi else None)
        elif repl_storage:
            write_output();repl_storage.finish_line(self.characters,repl['input_log'],output_log)
        else:write_output()
        if not repl_storage:self.characters.normalize(m,line,0x8e)
        dispatch=None;registers=None
        if loader is not None:
            parent=installed['main_registers'];registers=enter_dispatch(m,self.inputs['workspace_address'],installed['main_frame'],line,ebx=parent['ebx'],edi=parent['edi'],flags=parent['eflags'],inherited=parent)
            dispatch=DispatchStorage(m,self.characters,loader,loader_context)
            registers=dispatch.before_parser(dispatch.history(registers))
        self.point('parse')
        records=script_frame-12-4160
        parser_abi=ParserCallers(m,registers)if dispatch is not None else None
        identity=self.parser.parse(line,records,[ScanHistory(None,None,None)for _ in range(15)],abi=parser_abi)
        if identity!=-1:raise NotImplementedError('Interactive command transition requires the outer dispatcher')
        if dispatch is not None:
            registers=dispatch.quit_binding(dispatch.parser_return(registers,identity,line))
            registers=kill_vdso_entry(m,registers,libc_base=libc_base,tls_base=loader_context['tls_base'])
            if stdio and stdio.get('input_abi',{}).get('read_abi'):
                vdso_kernel_entry(m,registers)
        # console_analysis.cpp releases the cache in descending packed pairs.
        metals=len(bytes.fromhex(self.technology[1]))//236
        for index in reversed(range(metals*(metals+1)//2)):
            for name in ('xy','x','y'):self.release('cache.'+name,self.memory.u32(self.cache_arrays[name]['pointer_address']+4*index),'array')
        for name in ('xy','x','y'):self.release('cache.'+name+'.pointers',self.cache_arrays[name]['pointer_address'],'array')
        raise NotImplementedError('Process cleanup after the cache tables is not yet bound')

    def point(self,kind):
        address=self.inputs['workspace_address']
        regions=[dict(address=address,data=self.memory.read(address,4460)),dict(address=0x80d8660,data=self.memory.read(0x80d8660,120))]
        regions.extend(dict(address=r['address'],data=self.memory.read(r['address'],r['size']))for r in self.inputs.get('stdio_context',{}).get('regions',()))
        point=dict(kind=kind,events=len(self.events),regions=regions)
        if 'file_position'in self.inputs['stdin_stream']:point['stdin_position']=self.stdin_position
        self.points.append(point)
