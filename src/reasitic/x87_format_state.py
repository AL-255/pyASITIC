"""Masked x87 argument-copy/classification state for the original formatter.

This operates on raw 80-bit register slots and explicit XSAVE/FXSAVE bytes.
It covers the load/store/compare instructions surrounding binary64 decimal
conversion, not general x87 arithmetic. The independently measured AMD
error-pointer profile retains pointers during these masked operations.
Stack faults, unmasked exceptions and inexact extended-to-double stores
remain explicit source boundaries; no later target supplies their state.
"""
import struct

class X87FormatState:
    def __init__(self,image,*,pointer_mode):
        if pointer_mode!='masked-error-pointers':raise NotImplementedError('Other x87 pointer profiles require their source behavior')
        if len(image)<512:raise ValueError('Truncated FXSAVE/XSAVE image')
        if len(image)!=512:
            if len(image)<576:raise ValueError('Truncated XSAVE header')
            if struct.unpack_from('<Q',image,520)[0]:raise NotImplementedError('Compacted XSAVE needs its layout source')
        self.image=bytes(image);self.control,self.status=struct.unpack_from('<HH',image);self.tags=image[4];self.top=(self.status>>11)&7;self.active=False
        if self.control&0x3f!=0x3f:raise NotImplementedError('Unmasked x87 control needs its pending-exception source')
        self.slots=[None]*8
        for i in range(8):self.slots[(self.top+i)&7]=struct.unpack_from('<QH',image,32+16*i)

    def _begin(self):
        if self.status&0x80:raise NotImplementedError('Pending unmasked x87 exception needs its delivery source')
        self.active=True

    def _exception(self,flag):
        if flag&~self.control&0x3f:raise NotImplementedError('Unmasked x87 exception needs its instruction and delivery source')
        self.status|=flag

    def _position(self,index):
        if isinstance(index,bool)or not isinstance(index,int)or not 0<=index<8:raise ValueError('Invalid x87 stack index')
        return(self.top+index)&7

    def _get(self,index=0):
        position=self._position(index)
        if not self.tags&(1<<position):raise NotImplementedError('x87 stack underflow needs its masked/fault source')
        return self.slots[position]

    def _push(self,value):
        position=(self.top-1)&7
        if self.tags&(1<<position):raise NotImplementedError('x87 stack overflow needs its masked/fault source')
        self.top=position;self.tags|=1<<position;self.slots[position]=value;self.status&=~0x200

    def _pop(self):
        self._get();self.tags&=~(1<<self.top);self.top=(self.top+1)&7

    def fldcw(self,control):
        if isinstance(control,bool)or not isinstance(control,int)or not 0<=control<1<<16:raise ValueError('Invalid x87 control word')
        if control&0x3f!=0x3f:raise NotImplementedError('Unmasked x87 control needs its pending-exception source')
        self._begin();self.control=control

    def fld64(self,word):
        if isinstance(word,bool)or not isinstance(word,int)or not 0<=word<1<<64:raise ValueError('Expected binary64 bits')
        self._begin();negative=word>>63;exponent=(word>>52)&2047;sig=word&((1<<52)-1)
        if exponent==2047:
            if sig and not sig&(1<<51):self._exception(1)
            sig=((1<<63)|(sig<<11)|((1<<62)if sig else 0));exponent=0x7fff
        elif exponent:sig=((1<<52)|sig)<<11;exponent+=16383-1023
        elif sig:
            self._exception(2);shift=53-sig.bit_length();sig<<=shift+11;exponent=16383-1022-shift
        self._push((sig,exponent|(negative<<15)))

    def fld_st(self,index):
        self._begin();self._push(self._get(index))

    def fabs(self):
        self._begin();sig,exponent=self._get();self.slots[self.top]=(sig,exponent&0x7fff);self.status&=~0x200

    def fxch(self,index):
        self._begin();self._get();self._get(index);p=self._position(index);self.slots[self.top],self.slots[p]=self.slots[p],self.slots[self.top];self.status&=~0x200

    def fxam(self):
        self._begin();sig,exponent=self.slots[self.top];negative=bool(exponent&0x8000);exponent&=0x7fff
        if not self.tags&(1<<self.top):code=0x4100
        elif not exponent:code=0x4000 if not sig else 0x4400
        elif not sig>>63:code=0
        elif exponent==0x7fff:code=0x500 if sig==1<<63 else 0x100
        else:code=0x400
        self.status=(self.status&~0x4700)|code|(0x200 if negative else 0)

    def fucomi(self,index,eflags,*,pop=False):
        self._begin();a,b=self._get(),self._get(index)
        def classify(value):
            sig,e=value;e&=0x7fff
            if e and not sig>>63:raise NotImplementedError('Unsupported extended compare operand needs its original invalid-operation source')
            if not e and sig:raise NotImplementedError('Extended denormal compare needs its instruction source')
            if e==0x7fff and sig!=1<<63:
                if not sig&(1<<62):self._exception(1)
                return 'nan'
            return 'zero'if not sig else'number'
        ac,bc=classify(a),classify(b)
        if ac=='nan'or bc=='nan':flags=0x45
        elif ac==bc=='zero':flags=0x40
        elif a==b:flags=0x40
        else:
            an,bn=a[1]>>15,b[1]>>15
            if an!=bn:less=bool(an)
            else:less=((a[1]&0x7fff,a[0])<(b[1]&0x7fff,b[0]))^bool(an)
            flags=1 if less else 0
        self.status&=~0x200
        if pop:self._pop()
        return(eflags&~0x8d5)|flags

    def fst64(self,*,pop=False):
        self._begin();sig,exponent=self._get();negative=exponent>>15;exponent&=0x7fff;word=negative<<63
        if not sig:
            if exponent:raise NotImplementedError('Unsupported extended store operand needs its invalid-operation source')
        elif exponent==0x7fff:
            word|=0x7ff0000000000000
            if sig!=1<<63:
                if not sig>>63:raise NotImplementedError('Unsupported extended store operand needs its invalid-operation source')
                if not sig&(1<<62):self._exception(1)
                word|=((sig>>11)&((1<<52)-1))|(1<<51)
        elif not sig>>63:raise NotImplementedError('Extended denormal/unsupported store needs its instruction source')
        else:
            e=exponent-16383
            if -1022<=e<=1023 and not sig&2047:word|=((e+1023)<<52)|((sig>>11)&((1<<52)-1))
            elif -1074<=e<-1022 and not sig&((1<<(-e-1011))-1):word|=sig>>(-e-1011)
            else:raise NotImplementedError('Inexact extended-to-binary64 store needs its rounding/exception source')
        self.status&=~0x200
        if pop:self._pop()
        return word

    def fstp_st0(self):
        self._begin();self._get();self.status&=~0x200;self._pop()

    def fnstsw_ax(self,eax):return(eax&0xffff0000)|(self.status&~0x3800)|(self.top<<11)

    def serialize(self):
        image=bytearray(self.image);struct.pack_into('<HH',image,0,self.control,(self.status&~0x3800)|(self.top<<11));image[4]=self.tags
        for i in range(8):struct.pack_into('<QH',image,32+16*i,*self.slots[(self.top+i)&7])
        if len(image)>=520 and self.active:struct.pack_into('<Q',image,512,struct.unpack_from('<Q',image,512)[0]|1)
        return bytes(image)
