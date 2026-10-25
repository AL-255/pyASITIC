"""Original glibc binary64 decimal conversion, before its machine ABI binding.

Translates glibc 2.39 stdio-common/printf_fp.c and dbl2mpn.c,
Copyright (C) 1993-2024 Free Software Foundation, Inc., LGPL-2.1-or-later.
See web/GLIBC-LGPL-2.1.txt. Integer values retain explicit 32-bit limb
extents, scaling and hack_digit state. No host float/string formatting,
decimal logarithm, expected text or later native state supplies results.

This computes decimal digits and fields. It does not substitute for the
still-required original formatter stack/register/FP-state implementation.
"""
from functools import lru_cache

BITS=32
MASK=(1<<BITS)-1


def limb(value,index):return(value>>(BITS*index))&MASK
def limbs(value):return max(1,(value.bit_length()+BITS-1)//BITS)
def trailing(value):
    # The pinned i386 build uses TZCNT, including at 0x5a163 where the
    # low product limb can be zero. Its 32-bit zero result is 32.
    return(value&-value).bit_length()-1 if value else BITS


@lru_cache(maxsize=15)
def power(index):
    n=1<<index;value=10**n
    return value,limbs(value)+2,value.bit_length(),(10**(n-1)).bit_length()if index else 0


def extract_double(word):
    """The i386 two-limb __mpn_extract_double contract."""
    if isinstance(word,bool)or not isinstance(word,int)or not 0<=word<1<<64:raise ValueError('Expected binary64 bits')
    negative=word>>63;exponent=(word>>52)&2047;sig=word&((1<<52)-1)
    if exponent==2047:raise ValueError('Nonfinite argument does not enter MPN extraction')
    if exponent:sig|=1<<52;exponent-=1023
    elif sig:
        shift=53-sig.bit_length();sig<<=shift;exponent=-1022-shift
    else:exponent=0
    return sig,2,exponent,negative


class DecimalDigits:
    """The original frac/scale limb representation and destructive digit loop."""
    def __init__(self,word):
        sig,count,e,self.negative=extract_double(word);to_shift=1+count*BITS-53
        self.expsign=0;self.exponent=e;self.scale=0;self.scalesize=0;self.type='f'
        if e>2:self._large(sig,count,e,to_shift)
        elif e<0:self._small(sig,count,e,to_shift)
        else:self.frac=sig<<(e+to_shift);self.fracsize=count+1;self.exponent=0

    def _large(self,sig,count,e,shift):
        words,rest=divmod(e+shift,BITS);self.frac=sig<<(e+shift);self.fracsize=count+words+int(bool(rest and sig.bit_length()+rest>count*BITS))
        scaleexpo=0;exp10=0
        for index in range(12,-1,-1):
            value,size,p_expo,_=power(index)
            if e<scaleexpo+p_expo-1:continue
            if not self.scalesize:tmp=value<<64;tmpsize=size
            else:tmp=self.scale*value;tmpsize=self.scalesize+size-2-int(limb(tmp,self.scalesize+size-3)==0)
            if self.fracsize>tmpsize or(self.fracsize==tmpsize and self.frac>=tmp):
                self.scale,self.scalesize=tmp,tmpsize;cnt_h=BITS-limb(tmp,tmpsize-1).bit_length();scaleexpo=(tmpsize-2)*BITS-cnt_h-1;exp10|=1<<index
        self.exponent=exp10
        if not self.scalesize:return
        i=0
        while not limb(self.scale,i)and not limb(self.frac,i):i+=1
        cnt_h=BITS-limb(self.scale,self.scalesize-1).bit_length()
        if not cnt_h:
            self.scale>>=BITS*i;self.scalesize-=i;self.frac>>=BITS*i;self.fracsize-=i;return
        a,b=limb(self.scale,i),limb(self.frac,i);cnt_l=min(trailing(x)for x in(a,b)if x)
        if i==0 and BITS-cnt_h>cnt_l:
            self.scale<<=cnt_h;self.frac<<=cnt_h;self.fracsize+=int(bool(self.frac>>(BITS*self.fracsize)))
        elif BITS-cnt_h<=cnt_l:
            self.scale>>=BITS*i+BITS-cnt_h;self.scalesize-=i+1
            n=self.fracsize-i;self.frac>>=BITS*i+BITS-cnt_h;self.fracsize-=i+int(limb(self.frac,n-1)==0)
        else:
            self.scale>>=BITS*(i-1)+BITS-cnt_h;self.scalesize-=i
            n=self.fracsize-(i-1);self.frac>>=BITS*(i-1)+BITS-cnt_h;self.fracsize-=i-1+int(limb(self.frac,n-1)==0)

    def _small(self,sig,count,e,shift):
        self.frac=sig<<shift;self.fracsize=count+1;self.expsign=1;e=-e;exp10=0
        for index in range(12,0,-1):
            value,size,_,m_expo=power(index)
            if e>=m_expo:
                tmp=self.frac*value;tmpsize=self.fracsize+size-2-int(limb(tmp,self.fracsize+size-3)==0)
                cnt_h=BITS-limb(tmp,tmpsize-1).bit_length();incr=(tmpsize-self.fracsize)*BITS+BITS-1-cnt_h
                if incr==e+3:
                    # Native compares its two-limb topval with the top two
                    # product limbs. Keep both limbs in one exact integer.
                    topval=(10<<(2*BITS-4-cnt_h))
                    top=(limb(tmp,tmpsize-1)<<BITS)|limb(tmp,tmpsize-2)
                if incr<e+3 or(incr==e+3 and top<topval):
                    e-=incr;exp10|=1<<index
                    if e<0:cnt_h-=e
                    i=0
                    while not limb(tmp,i):i+=1
                    if cnt_h==BITS-1:self.frac=tmp>>(BITS*i);self.fracsize=tmpsize-i
                    else:
                        cnt_l=trailing(limb(tmp,i));k=BITS-1-cnt_h
                        if i==0 and k>cnt_l:self.frac=tmp<<(cnt_h+1);self.fracsize=tmpsize+1
                        elif k<=cnt_l:self.frac=tmp>>(BITS*i+k);self.fracsize=tmpsize-i
                        else:self.frac=tmp>>(BITS*(i-1)+k);self.fracsize=tmpsize-(i-1)
            if e<=0:break
        if e>0:
            tmp=self.frac*10;tmpsize=self.fracsize;tmp&=(1<<(tmpsize*BITS))-1;k=min(4,e);cnt_l=trailing(limb(tmp,0))
            if cnt_l<k:
                self.frac=tmp<<(BITS-k);tmpsize+=int(bool(self.frac>>(tmpsize*BITS)))
            else:self.frac=tmp>>k
            self.fracsize=tmpsize;exp10|=1
        self.exponent=exp10

    def digit(self):
        if self.expsign and self.type=='f':
            old=self.exponent;self.exponent-=1
            if old>0:return 0
        if not self.scalesize:
            high=limb(self.frac,self.fracsize-1);self.frac=(self.frac&((1<<((self.fracsize-1)*BITS))-1))*10
        else:
            if self.fracsize<self.scalesize:high=0
            else:
                high,self.frac=divmod(self.frac,self.scale);self.fracsize=self.scalesize
                while self.fracsize and not limb(self.frac,self.fracsize-1):self.fracsize-=1
                if not self.fracsize:self.fracsize=1;return high
            self.frac*=10;self.fracsize+=int(bool(self.frac>>(self.fracsize*BITS)))
        if not 0<=high<=9:raise ValueError('Original decimal digit is outside 0..9')
        return high

    def remainder(self):return self.fracsize>1 or bool(self.frac)


def round_away(negative,odd,half,more,mode):
    if mode==0:return half and(more or odd)
    if mode==1:return negative and(half or more)
    if mode==2:return not negative and(half or more)
    if mode==3:return False
    raise ValueError('Unknown x87 rounding mode')


def format_binary64(word,spec='g',precision=-1,width=0,flags='',rounding=0):
    """C-locale f/e/g output from binary64 bits and explicit earlier controls."""
    if spec not in'eEfFgG':raise NotImplementedError('Other floating specifiers require their original source')
    if any(isinstance(v,bool)or not isinstance(v,int)or not -(1<<31)<=v<(1<<31)for v in(precision,width)):raise ValueError('Floating width and precision must be int32 values')
    if any(ch not in'-+ 0#'for ch in flags):raise NotImplementedError('Localized/grouped floating fields require their original source')
    if isinstance(word,bool)or not isinstance(word,int)or not 0<=word<1<<64:raise ValueError('Expected binary64 bits')
    negative=bool(word>>63);sign='-'if negative else'+'if'+'in flags else' 'if' 'in flags else'';left='-'in flags;alt='#'in flags;pad='0'if'0'in flags and not left else' '
    if(word>>52)&2047==2047:
        special='nan'if word&((1<<52)-1)else'inf'
        if spec.isupper():special=special.upper()
        spaces=' '*max(0,width-len(sign)-3)
        return(sign+special+spaces if left else spaces+sign+special).encode('ascii')
    p=DecimalDigits(word);lower=spec.lower();dig_max=0x7fffffff;significant=1
    if lower=='e':p.type=spec;intdig_max=1;frac_min=frac_max=6 if precision<0 else precision
    elif lower=='f':p.type='f';frac_min=frac_max=6 if precision<0 else precision;intdig_max=p.exponent+1 if not p.expsign else 1
    else:
        dig_max=6 if precision<0 else max(1,precision)
        if(not p.expsign and p.exponent>=dig_max)or(p.expsign and p.exponent>4):p.type='E'if spec.isupper()else'e';frac_max=dig_max-1;intdig_max=1
        else:p.type='f';intdig_max=p.exponent+1 if not p.expsign else 0;frac_max=dig_max-intdig_max
        frac_min=frac_max if alt else 0;significant=0
    # The two leading spare bytes reproduce the source's rounding cursor.
    out=['\0','\0'];start=cursor=2;integer_no=0
    def store(at,ch):
        if at>=len(out):out.extend(['\0']*(at+1-len(out)))
        out[at]=ch
    def put(ch):
        nonlocal cursor
        store(cursor,ch)
        cursor+=1
    if not p.expsign or p.type!='f':
        while integer_no<intdig_max:integer_no+=1;put(chr(48+p.digit()))
        significant=1
        if alt or frac_min>0 or(frac_max>0 and p.remainder()):put('.')
    else:put('0');p.exponent-=1;put('.')
    fractional_no=added=0
    while fractional_no<frac_min+added or(fractional_no<frac_max and p.remainder()):
        fractional_no+=1;ch=chr(48+p.digit());put(ch)
        if ch!='0':significant=1
        elif not significant:
            frac_max+=1
            if frac_min>0:added+=1
    last=out[cursor-1]if out[cursor-1]!='.'else out[cursor-2];nxt=p.digit()
    more=True if nxt not in(0,5)else False if p.fracsize==1 and not p.frac else bool(p.frac)if not p.scalesize else True
    if round_away(negative,(ord(last)-48)&1,nxt>=5,more,rounding):
        at=cursor
        if fractional_no>0:
            removed=0;at-=1
            while out[at]!='.'and out[at]=='9':out[at]='0';removed+=1;at-=1
            if removed==frac_min and added>0:added-=1
            if out[at]!='.':out[at]=chr(ord(out[at])+1)
            elif lower=='g'and p.type=='f'and alt and at==start+1 and out[start]=='0':added-=1
        if fractional_no==0 or out[at]=='.':
            if out[at-1]=='.':at-=1
            at-=1
            while at>=start and out[at]=='9':out[at]='0';at-=1
            if at>=start:out[at]=chr(ord(out[at])+1)
            else:
                if p.type!='f':
                    out[start]='1';p.exponent+=-1 if p.expsign else 1
                    if not p.exponent:p.expsign=0
                elif integer_no==dig_max:
                    start-=1;out[start]='.';start-=1;out[start]='1'
                    if alt or fractional_no>0:store(start+integer_no+2,'0');fractional_no+=1
                    fractional_no+=integer_no;integer_no=1;frac_max=intdig_max-integer_no;p.exponent+=1;p.type='E'if spec.isupper()else'e'
                else:start-=1;out[start]='1';integer_no+=1
                if integer_no+fractional_no>dig_max:
                    excess=integer_no+fractional_no-dig_max;cursor-=excess;fractional_no-=excess
    while fractional_no>frac_min+added and out[cursor-1]=='0':cursor-=1;fractional_no-=1
    if not fractional_no and not alt and out[cursor-1]=='.':cursor-=1
    if p.type!='f':
        if p.expsign and p.exponent==4 and lower=='g':
            text='0.0001';old=cursor-start
            for i,ch in enumerate(text):store(start+i,ch)
            if old>=2:
                for i in range(old-2):store(start+6+i,'0')
                cursor+=4
            else:cursor+=5
        else:
            put(p.type);put('-'if p.expsign else'+');scale=10
            while scale<=p.exponent:scale*=10
            if p.exponent<10:put('0')
            else:
                while scale>10:scale//=10;put(chr(48+p.exponent//scale));p.exponent%=scale
            put(chr(48+p.exponent))
    text=''.join(out[start:cursor]);spaces=pad*max(0,width-len(sign)-len(text))
    return(sign+text+spaces if left else sign+spaces+text if pad=='0'else spaces+sign+text).encode('ascii')
