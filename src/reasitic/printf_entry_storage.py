"""Pinned i386 printf/fprintf/vfprintf entry frames and their real child.

Follows glibc 2.39 stdio-common printf.c, fprintf.c and vfprintf.c,
LGPL-2.1-or-later; see web/GLIBC-LGPL-2.1.txt. Every argument and binding
comes from live earlier guest memory. The shared parent produces FP state.
"""
from .signal_install_storage import add_flags,subtract_flags
from .vfprintf_storage import VfprintfStorage


class PrintfEntryStorage(VfprintfStorage):
    def entry(self,registers):
        m=self.m;r=dict(registers);s=r['esp'];offset=r['eip']-self.libc
        if offset not in (0x57db0,0x57670,0x5e680):raise NotImplementedError('Alternate printf entry needs its source ABI')
        if offset==0x57db0:
            # __x86.get_pc_thunk.ax leaves its return word in the caller's
            # unused local space; the subsequent argument pushes do not erase it.
            m.put_u32(s-4,self.libc+0x57db9)
            r['eax']=self.got;r['edx']=s+8
            file_binding=m.u32(self.got+0xb8);file=m.u32(file_binding)
            fmt=m.u32(s+4);arguments=s+8;return_pc=self.libc+0x57dd9
            r['eflags']=add_flags(self.libc+0x57db9,0x1d807b,r['eflags']);r['eax']=file_binding
        else:
            file=m.u32(s+4);fmt=m.u32(s+8)
            if offset==0x57670:arguments=s+12;r['eax']=arguments;return_pc=self.libc+0x5768b
            else:arguments=m.u32(s+12);return_pc=self.libc+0x5e69a
        r['eflags']=subtract_flags(s,12,r['eflags'])
        for displacement,value in ((16,0),(20,arguments),(24,fmt),(28,file),(32,return_pc)):m.put_u32(s-displacement,value)
        r.update(esp=s-32,eip=self.libc+0x62110)
        r=self.file._child('vfprintf',r,self.vfprintf)
        return dict(r,esp=s+4,eip=m.u32(s),eflags=add_flags(s-28,28,r['eflags']))
