"""Source port-header text and the original i386 caller's filename stack writes."""
import bisect,datetime,math,re,struct
from .command_storage import string

_FORMAT=re.compile(rb'%([-+ #0]*)([0-9]*)(?:\.([0-9]+))?(?:[lhL]*)([sdiufgeE%])')


def printf(fmt,*args):
    result=bytearray();position=0;argument=iter(args)
    for match in _FORMAT.finditer(fmt):
        result+=fmt[position:match.start()];flags,width,precision,kind=match.groups();position=match.end()
        if kind==b'%':result+=b'%';continue
        value=next(argument)
        if kind==b's':
            raw=value.encode()if isinstance(value,str)else bytes(value);raw=raw.split(b'\0',1)[0]
            if precision is not None:raw=raw[:int(precision)]
            result+=raw.ljust(int(width or b'0'))if b'-'in flags else raw.rjust(int(width or b'0'));continue
        spec=(b'%'+flags+width+(b'.'+precision if precision is not None else b'')+kind).decode()
        if kind in (b'f',b'g',b'e',b'E')and math.isnan(value):
            text='-nan'if struct.pack('<d',value)[-1]&128 else'nan'
            result+=(text.ljust(int(width or b'0'))if b'-'in flags else text.rjust(int(width or b'0'))).encode();continue
        result+=(spec%value).encode('ascii')
    result+=fmt[position:];return bytes(result)


class NativePortStack:
    """Static i386 call layout, not an observed timestamp lookup.

    Original replace at 0x80b2214..0x80b221a pushes length/source/destination
    and the memcpy return address. The handler's replace tail starts at
    EBP-1192; the two header callers reuse its source-argument or return slot.
    Read-only hardware watches independently verify both writers.
    """
    MEMCPY_RETURN=0x80b221f

    def __init__(self,memory,handler_frame):self.memory=memory;self.frame=handler_frame
    def filename_copy(self,source,destination,length):
        if not length:raise NotImplementedError('Empty native filename-copy stack path is not reproduced')
        for offset,value in ((-1196,length),(-1200,source),(-1204,destination),(-1208,self.MEMCPY_RETURN)):
            self.memory.put_u32(self.frame+offset,value)
    def timestamp(self,command):
        if command not in (528,524):raise NotImplementedError('Native port caller stack layout is not bound')
        address=self.frame-(1208 if command==524 else 1200)
        return address,struct.unpack('<i',self.memory.read(address,4))[0]

    def driver_entry(self,driver,arguments,frequency,termination=0.,*,libc_base):
        """First sweep sample's actual i386 call layout and argument stores.

        Dispatcher 0x805bd40 reserves 0x444 bytes and saves three registers.
        Ground export 0x8087770 calls wrapper 0x8052b60; transformer export
        0x8087ad0 calls CALCTRANS directly. The pending fflush argument in
        the ground path survives until after the analysis call.
        """
        sp=self.frame-0x444-3*4
        if driver=='calctrans':
            frame=sp-5*4-4-4  # export arguments, CALL, saved EBP
            sp=frame-0x24-3*4
            entry=sp-4-16-3*4-4  # print slot, two doubles, shapes, CALL
            caller=0x8087bb9
            data=struct.pack('<3I2d',*arguments,frequency,termination)
            self.memory.write(entry+4,data);self.memory.write(entry+32,b'\1\0')
        elif driver=='pi2':
            export_frame=sp-2*4-4-4
            sp=export_frame-0x28-3*4
            flush_entry=sp-4-4  # FILE argument and fflush CALL
            sync_slot=flush_entry-4-3*4-12-12-4-4
            # Pinned i386 fflush: saved EBP/registers, twelve local bytes,
            # twelve alignment bytes, FILE argument and virtual sync CALL.
            self.memory.put_u32(sync_slot,(libc_base+0x75bd2)&0xffffffff)
            frame=sp-4-6*4-4-4  # fflush, wrapper arguments, CALL, EBP
            entry=frame-4-3*4-4-8-2*4-4
            caller=0x8052c27
            # The preceding fflush's virtual _IO_SYNC CALL at libc+0x75bcf
            # writes this return slot. PUSHW 0 later replaces only its low
            # half, preserving the high bytes in the print-flag padding.
            assert sync_slot==entry+20
            self.memory.write(entry+4,struct.pack('<2Id',*arguments,frequency));self.memory.write(entry+20,b'\0\0')
        else:raise ValueError('Unsupported port analysis driver')
        self.memory.put_u32(entry,caller)
        return dict(esp=entry&0xffffffff,ebp=frame&0xffffffff,caller=caller,pc=0x8051280 if driver=='calctrans'else 0x8050b2c)


def calendar(timestamp,tzif):
    def block(offset,width):
        header=tzif[offset:offset+44]
        if header[:4]!=b'TZif':raise ValueError('Invalid earlier timezone file')
        gmt,std,leaps,count,types,chars=struct.unpack('>6I',header[20:44])
        if leaps:raise NotImplementedError('Leap-second timezone conversion is not implemented')
        start=offset+44;times=struct.unpack('>'+('q'if width==8 else'i')*count,tzif[start:start+width*count]);start+=width*count
        indices=tzif[start:start+count];start+=count
        records=[struct.unpack_from('>iBB',tzif,start+6*i)for i in range(types)]
        return times,indices,records,start+6*types+chars+gmt+std
    times,indices,types,end=block(0,4)
    if tzif[4:5]in (b'2',b'3',b'4'):times,indices,types,end=block(end,8)
    if not times or timestamp<times[0]:index=next((i for i,r in enumerate(types)if not r[1]),0)
    else:index=indices[bisect.bisect_right(times,timestamp)-1]
    date=datetime.datetime(1970,1,1)+datetime.timedelta(seconds=timestamp+types[index][0])
    day=('Mon','Tue','Wed','Thu','Fri','Sat','Sun')[date.weekday()];month=('Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec')[date.month-1]
    return f'{day} {month} {date.day:2d} {date.hour:02d}:{date.minute:02d}:{date.second:02d} {date.year:04d}\n'.encode()


def header(shape,memory,technology,technology_name,directory,cells,date,*,transformer=False):
    out=[];p=lambda fmt,*args:out.append(printf(fmt,*args))
    d=lambda offset:struct.unpack('<d',memory.read(shape+offset,8))[0]
    i=lambda offset:struct.unpack('<i',memory.read(shape+offset,4))[0]
    p(b'\n!*************************************************************************')
    p(b'\n!! ASITIC Ver %s\n!!  Data generated by the <%s> command in',b'10.20.99.0.0.0',b'2PortTrans'if transformer else b'2Port')
    p(b' <slow> mode.');p(b'\n!! Generated on %s',date.rstrip(b'\n\r\t'))
    p(b'\n!# Spiral Data:\tName = <%s>',string(memory,shape))
    kind=i(0x50);description={0:b', Square Spiral Inductor',1:b', Polygon Spiral Inductor',2:b', Wire',3:b', Transformer',4:b', Capacitor',5:b', Balun',10:b', 3D Mirror Transformer',14:b', Via',15:b', Pad',16:b', Symmetric Square Inductor',17:b', Symmetric Polygon Inductor',18:b', Multi-Metal Square Spiral Inductor'}.get(kind,b', User-defined Structure')
    p(description)
    if kind in (1,17):p(b', Radius = %5.2lf',d(0x80))
    elif kind==2:p(b'\n!# L1 = %5.2lf',d(0x70))
    elif kind in (0,3,4,5,10,14,15,16,18):p(b'\n!# L1 = %5.2lf, L2 = %5.2lf',d(0x70),d(0x78))
    p(b', Origin = <%5.2lf,%5.2lf>',d(0x54),d(0x5c));p(b'\n!# Sides = %3d',i(0x64));p(b', Metal = %3d, Exit Metal = %3d',i(0x68),i(0x6c))
    p(b'\n!# W = %5.2lf, S = %5.2lf, N = %5.2lf',d(0x88),d(0x90),d(0x98));p(b'\n!# Theta = %5.2lf, Phase = %3d',d(0xa0),i(0xac))
    p(b'\n!# Technolog File Data <%s> @ <%s>',technology_name,directory)
    p(b'\n!# Max Inductor Cell Size: <length> = %lf, <width> %lf, <thickness> = %lf',cells['length_cell'],cells['width_cell'],cells['thickness_cell'])
    p(b'\n!# Max Capacitor Cell Size: <length> = %lf,<width> %lf',cells['capacitance_length_cell'],cells['capacitance_width_cell'])
    p(b'\n!# Metal Layers');substrates,metals=map(bytes.fromhex,technology)
    for index in range(len(metals)//236):
        m=metals[index*236:(index+1)*236];name=m[:80].split(b'\0',1)[0];color=m[80:160].split(b'\0',1)[0]
        layer=struct.unpack_from('<i',m,160)[0];mz,thickness,rs=struct.unpack_from('<3d',m,168)
        p(b'\n!# Name=%-8s  Met=%d  Lyr=%3d  Mz=%4.2lf  T=%4.2lf  RS=%4.2lf  Col=%-8s',name,index,layer,mz,thickness,rs,color)
    p(b'\n!# Substrate Layers')
    for index in range(len(substrates)//40):p(b'\n!# Lyr=%5d  Eps=%4.2lg  Rho=%4.2lg  DZ=%4.2lg  T=%4.2lg',index,*struct.unpack_from('<4d',substrates,40*index+4))
    p(b'\n!! Cell size:  L = %4.2lf \t W = %4.2lf \t T = %4.2lf',cells['length_cell'],cells['width_cell'],cells['thickness_cell'])
    p(b'\n!! Cap Cell size:  L = %4.2lf \t W = %4.2lf',cells['capacitance_length_cell'],cells['capacitance_width_cell'])
    p(b'\n!*************************************************************************')
    p(b'\n%-11.11s%-11.11s%-11.11s%-11.11s%-11.11s%-11.11s%-11.11s%-11.11s%-11.11s',b'# GHZ S RI R 50\n! f (GHz)',b'S11r',b'S11i',b'S12r',b'S12i',b'S21r',b'S21i',b'S22r',b'S22i')
    return b''.join(out)
