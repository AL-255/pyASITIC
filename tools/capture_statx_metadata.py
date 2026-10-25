"""Earlier external file facts, rather than later native stat buffers."""
OBSERVER=r'''
def statx_metadata():
 raw=ctypes.create_string_buffer(256);path=('/proc/%d/fd/0'%gdb.selected_inferior().pid).encode()
 if libc.statx(-100,path,0,0x7ff,ctypes.byref(raw)):raise OSError(ctypes.get_errno())
 data=raw.raw
 if any(data[160:])or any(data[30:32]):raise RuntimeError('Additional statx ABI fields need an explicit schema')
 for p in (64,80,96,112):
  if any(data[p+12:p+16]):raise RuntimeError('Unexpected statx timestamp padding')
 result={}
 for name,offset,fmt in (('mask',0,'I'),('blksize',4,'I'),('attributes',8,'Q'),('nlink',16,'I'),('uid',20,'I'),('gid',24,'I'),('mode',28,'H'),('ino',32,'Q'),('size',40,'Q'),('blocks',48,'Q'),('attributes_mask',56,'Q'),('rdev_major',128,'I'),('rdev_minor',132,'I'),('dev_major',136,'I'),('dev_minor',140,'I'),('mnt_id',144,'Q'),('dio_mem_align',152,'I'),('dio_offset_align',156,'I')):
  result[name]=struct.unpack_from('<'+fmt,data,offset)[0]
 for name,p in (('atime',64),('btime',80),('ctime',96),('mtime',112)):
  sec,nsec=struct.unpack_from('<qI',data,p);result[name]=dict(sec=sec,nsec=nsec)
 return dict(query_mask=0x7ff,fields=result)
'''
