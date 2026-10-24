"""Successful fully buffered binary stream stores from i386 glibc 2.39.

Translation of _IO_new_file_xsputn / _IO_file_xsgetn (libio/fileops.c),
Copyright (C) 1993-2024 Free Software Foundation, Inc., LGPL-2.1-or-later.
See web/GLIBC-LGPL-2.1.txt. Distributed without warranty of merchantability
or fitness for a particular purpose. Python translation Copyright (C) 2026
pyASITIC authors. No line buffering, backup areas, short IO or failures here.

Unknown incoming file bytes stay unknown; header bytes must not be invented
just to fill a buffer. Direct block transfers deliberately bypass the buffer.
"""


class FileBytes:
    def __init__(self,chunks):
        self.chunks=[];self.size=0
        for data,size in chunks:
            if data is not None and len(data)!=size:raise ValueError('File chunk length differs from its storage')
            self.chunks.append((self.size,self.size+size,data));self.size+=size

    def store(self,memory,address,offset,size):
        end=offset+size
        for start,stop,data in self.chunks:
            lo=max(start,offset);hi=min(stop,end)
            if lo>=hi:continue
            if data is None:memory.write_unknown(address+lo-offset,hi-lo)
            else:memory.write(address+lo-offset,data[lo-start:hi-start])


def write_buffer(memory,address,capacity,file):
    """Run the same fwrite chunk boundaries; close flushes without clearing."""
    pointer=0;putting=False
    for start,stop,_ in file.chunks:
        want=stop-start;position=start
        if not want:continue
        count=min(capacity-pointer,want)if putting else 0
        if count:file.store(memory,address+pointer,position,count);pointer+=count;position+=count;want-=count
        if want:
            # Overflow initializes or flushes the put area before block IO.
            putting=True;pointer=0
            direct=want-want%capacity if capacity>=128 else want
            position+=direct;want-=direct
            if want:file.store(memory,address,position,want);pointer=want


def read_buffer(memory,address,capacity,file):
    """Run successful fread calls and underflow fills, retaining unused tail."""
    position=pointer=end=0
    for start,stop,_ in file.chunks:
        want=stop-start
        while want:
            available=end-pointer
            if want<=available:pointer+=want;break
            want-=available;pointer+=available
            if want<capacity:
                count=min(capacity,file.size-position)
                if not count:raise ValueError('Unexpected EOF in successful cache read')
                file.store(memory,address,position,count);position+=count;pointer=0;end=count
            else:
                pointer=end=0;count=want-want%capacity if capacity>=128 else want
                count=min(count,file.size-position)
                if not count:raise ValueError('Unexpected EOF in successful cache read')
                position+=count;want-=count
