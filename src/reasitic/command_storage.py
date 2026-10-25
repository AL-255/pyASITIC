"""Native fixed command records, normalization and typed argument stores.

Follows command_runtime.cpp/technology_text.cpp. Incoming records and scan
history are caller state. Character tables are explicit locale inputs. The
default scanner covers ordinary C decimal/hex numbers; a caller may supply
the scan boundary for other libc/locale contracts. No history is invented
after a failed conversion, and no numeric value word is zeroed by tokenizing.
"""
from dataclasses import dataclass
import math,re,struct
from .command_catalog import CATALOG
from .command_numbers import binary32
from .retained_scalar import Real


def string(memory,address):
    out=bytearray()
    while True:
        value=memory.read(address+len(out),1)
        if value==b'\0':return bytes(out)
        out+=value


class Characters:
    def __init__(self,inputs):
        self.classification=struct.unpack('<384H',bytes.fromhex(inputs['classification']))
        self.upper=struct.unpack('<384i',bytes.fromhex(inputs['uppercase']))
        self.lower=struct.unpack('<384i',bytes.fromhex(inputs['lowercase']))

    def normalize(self,memory,address,flags,*,abi=None):
        out=source=address;space=content=quoted=False;quote=0
        while True:
            c=memory.read(source,1)[0];source+=1
            if abi is not None:abi.source(source)
            if not c:break
            if quoted:
                memory.write(out,bytes([c]));out+=1
                if c==quote:
                    quoted=False
                    if abi is not None:abi.end_quote()
                continue
            if flags&16 and c in (34,39):
                memory.write(out,bytes([c]));out+=1;space=False;content=True;quoted=True;quote=c
                if abi is not None:abi.begin_quote(c)
                continue
            index=c if c<128 else c-256;classification=self.classification[index+128]
            if abi is not None:abi.character(index)
            if classification&0x2000 and index>=0:
                if flags&1 or flags&2 and not content:continue
                if flags&8:
                    if not space:memory.write(out,b' ');out+=1;space=True
                    continue
                if flags&128 and classification&2:continue
            else:
                space=False;content=True
                if abi is not None:abi.content()
                if classification&2 and index>=0:
                    if flags&128:continue
                elif index>=0:
                    if flags&32:c=self.upper[index+128]&255
                    if flags&64:c=self.lower[(c if c<128 else c-256)+128]&255
            memory.write(out,bytes([c]));out+=1
        memory.write(out,b'\0')
        if flags&4:
            while True:
                out-=1;c=memory.read(out,1)[0];index=c if c<128 else c-256
                if abi is not None:abi.trim(c,index,self.classification[index+128])
                if not self.classification[index+128]&0x2000 or index<0 or out<address:break
                memory.write(out,b'\0')
        return address


@dataclass
class ScanHistory:
    number: float | None
    integer: int | None
    character: int | None


_FLOAT=re.compile(rb'[+-]?(?:inf(?:inity)?|nan|0[xX](?:[0-9a-f]+(?:\.[0-9a-f]*)?|\.[0-9a-f]+)(?:p[+-]?[0-9]+)?|(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:e[+-]?[0-9]+)?)',re.I)


def scan(text,kind):
    if kind=='character':return text[0]if text else None
    text=text.lstrip(b' \t\n\r\v\f')
    match=(_FLOAT if kind=='number'else re.compile(rb'[+-]?[0-9]+')).match(text)
    if match is None:return None
    token=match.group()
    if kind=='integer':return max(-0x80000000,min(0x7fffffff,int(token)))
    rest=text[match.end():]
    if rest[:1].lower()in (b'e',b'p'):
        raise NotImplementedError('Incomplete libc floating scan exponent needs the caller scan boundary')
    value=token.decode('ascii')
    return float.fromhex(value)if b'0x'in token.lower()else float(value)


def lookup(text):
    return next((row for row in CATALOG if text in tuple(a.encode()for a in row[1])),None)


class CommandStorage:
    def __init__(self,memory,characters,find_shape,warn,*,frequency_scale=1e9,length_scale=1e-6,grid_size=.1,snap=True,scanner=scan,reset_mesh=None):
        self.memory=memory;self.characters=characters;self.find_shape=find_shape;self.warn=warn
        self.frequency_scale=frequency_scale;self.length_scale=length_scale;self.grid_size=grid_size;self.snap=snap
        self.scanner=scanner;self.reset_mesh=reset_mesh

    def _tokens(self,line):
        m=self.memory;p=line
        while True:
            while m.read(p,1)in (b' ',b','):p+=1
            if m.read(p,1)==b'\0':return
            start=p
            while m.read(p,1)not in (b'\0',b' ',b','):p+=1
            end=m.read(p,1);m.write(p,b'\0');yield start
            if end==b'\0':return
            p+=1

    def parse_argument(self,address,kind,history):
        m=self.memory;c=self.characters
        if kind in (0,1,2,8,9):c.normalize(m,address,32)
        text=string(m,address)
        if kind in (0,8):
            shape=self.find_shape(text)
            if shape is None:
                self.warn((b'Error:  Could not Find Ground Spiral <'if kind==8 else b'Error:  Could not Find Spiral <')+text+b'>.');return False
            m.put_u32(address+256,shape)
            if kind==8:
                if self.reset_mesh is None:raise NotImplementedError('Ground command parsing requires source mesh reset')
                self.reset_mesh(shape)
            return True
        if kind in (1,3):return bool(text)
        if kind==9:
            value=1 if text in (b'TRUE',b'T',b'YES',b'ON',b'Y')else 0 if text in (b'FALSE',b'F',b'NO',b'OFF',b'N')else None
            if value is None:self.warn(b'Error:  <'+text+b'> is not a member of the set:  (true, yes, on, false, no, off)');return False
            m.write(address+256,bytes([value]));return True
        if kind not in (2,4,5,6,7,10):self.warn(b'Error:  Unknown argument type.');return False
        field='character'if kind==2 else'integer'if kind==6 else'number'
        value=self.scanner(text,field)
        if value is not None:setattr(history,field,value)
        value=getattr(history,field)
        if value is None:raise NotImplementedError('Failed native scan requires the earlier caller '+field+' slot')
        if kind==2:
            if not 65<=value<=90:return False
            m.write(address+256,bytes([value]));return True
        if kind==6:m.put_u32(address+256,value);return True
        number=Real(value)
        if kind==5:number*=Real(self.frequency_scale)
        elif kind==7:number=(number*Real(self.length_scale))*Real(1e6)
        elif kind==10:
            if number>0 or number<0:
                quotient=number/Real(360.);whole=Real(float(quotient)if quotient.kind else float(math.floor(quotient.value)))
                number=number-whole*Real(360.)if number>0 else whole*Real(360.)+number
            else:number=Real(0.)
        result=binary32(number);m.write(address+256,struct.pack('<f',result))
        if kind==5 and Real(value)<=Real(1e-10):self.warn(b'Error 2102:  Frequency must be positive.');return False
        if kind==7 and self.snap:
            grid=Real(self.grid_size);steps=float(math.floor(((grid*Real(.5)+Real(result))/grid).value));result=binary32(Real(steps)*grid)
            m.write(address+256,struct.pack('<f',result))
        if kind==10:m.write(address+256,struct.pack('<f',binary32(Real(result)*Real(float.fromhex('0x1.1df46a2529d39p-6')))))
        return True

    def parse(self,line,records,histories):
        m=self.memory;c=self.characters;c.normalize(m,line,0x8e)
        if m.read(line,1)in (b'\0',b'#'):return -3
        tokens=self._tokens(line)
        try:first=next(tokens)
        except StopIteration:raise ValueError('Native delimiter-only command has a null token')
        c.normalize(m,first,32);m.write(records,string(m,first)+b'\0');count=0
        for token in tokens:
            target=records+260*(count+1);value=string(m,token)[:256]
            m.write(target,value+b'\0'*(256-len(value)));count+=1
            if count==15:break
        row=lookup(string(m,records))
        if row is None:return -2
        identity,_,minimum,maximum,usage,types=row
        if not minimum<=count<=maximum:self.warn(('Invalid Argument(s):  '+usage).encode());return -3
        m.put_u32(records+256,count)
        for index in range(min(count,maximum)):
            if not self.parse_argument(records+260*(index+1),types[index],histories[index]):return -3
        return identity
