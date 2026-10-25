"""Native parser caller and catalog prologue stores in guest Memory.

Follows command_runtime.cpp and the pinned i386 program. Tokenizer/string
callee bodies remain separate operations; no returned native snapshot or
later expected stack word supplies these caller effects.
"""
from .dispatch_storage import logical_flags
from .signal_install_storage import add_flags,subtract_flags

MASK=0xffffffff
COMPARISON_PCS=(0x805bcd6,0x805bce9,0x805bcfc,0x805bd0f)


def parser_to_tokenizer(memory,registers):
    m=memory;r=dict(registers);s=r['esp'];f=s-4
    if r['eip']!=0x8086fc0:raise ValueError('Parser caller needs its actual entry PC')
    m.put_u32(f,r['ebp'])
    for offset,key in((20,'edi'),(24,'esi'),(28,'ebx')):m.put_u32(f-offset,r[key])
    records=m.u32(f+12);line=m.u32(f+8)
    for offset,value in((32,f-4),(36,records),(40,line),(44,0x8086fd9)):m.put_u32(f-offset,value)
    r.update(ebp=f,esi=records,eax=f-4,esp=f-44,eip=0x808769c,eflags=subtract_flags(f,16,r['eflags']))
    return r


def tokenizer_return_to_catalog(memory,registers):
    m=memory;r=dict(registers);s=r['esp'];value=r['eax']&255
    if r['eip']!=0x8086fd9:raise ValueError('Tokenizer caller needs its actual return PC')
    if not value:raise NotImplementedError('Failed tokenization needs the parser error return')
    flags=logical_flags(value,add_flags(s,12,r['eflags']));flags=(flags&~0x80)|(value&0x80)
    m.put_u32(s+8,r['esi']);m.put_u32(s+4,0x8086ff6)
    r.update(esp=s+4,eip=0x805bcc0,eflags=flags)
    return r


def _catalog_prologue(m,s,*,ebp,edi,esi,ebx):
    f=s-4;m.put_u32(f,ebp)
    for offset,value in((4,edi),(8,esi),(12,ebx)):m.put_u32(f-offset,value)
    return f


def catalog_to_comparison(memory,registers):
    m=memory;r=dict(registers);s=r['esp']
    if r['eip']!=0x805bcc0:raise ValueError('Catalog lookup needs its actual entry PC')
    f=_catalog_prologue(m,s,**{k:r[k]for k in('ebp','edi','esi','ebx')})
    records=m.u32(f+8);head=m.u32(0x80cbac0)
    if head==0xfffffffe:raise NotImplementedError('Empty catalog returns before its first comparison')
    r.update(ebp=f,esp=f-12,edi=records,esi=0,ebx=0,eip=0x805bcd6,eflags=logical_flags(0,r['eflags']))
    return r


def comparison_argument(memory,registers):
    r=dict(registers)
    if r['eip']not in COMPARISON_PCS:raise ValueError('Catalog argument needs its original PUSH instruction')
    r['esp']=(r['esp']-4)&MASK;memory.put_u32(r['esp'],r['edi']);r['eip']+=1
    return r


class ParserCallers:
    """Known caller/prologue stores around the semantic parser's children.

    Only preserved registers and logical argument/count/lookup events are
    consumed here. This does not manufacture volatile child returns or
    claim to execute tokenizer/strcmp/scanner instruction frames.
    """
    def __init__(self,memory,registers):
        self.m=memory;self.initial=dict(registers);self.frame=registers['esp']-4
        self.line=memory.u32(registers['esp']+4);self.records=memory.u32(registers['esp']+8)
        self.tokenizer_registers=parser_to_tokenizer(memory,registers)
        self.comparisons=[];self.lookup_frame=None;self.argument_count=None

    def validate(self,line,records):
        if(line,records)!=(self.line,self.records):raise ValueError('Semantic parser arguments differ from the actual caller frame')

    def count(self,value):self.argument_count=value;self.m.put_u32(self.frame-4,value)

    def begin_lookup(self):
        if self.argument_count is None:raise ValueError('Catalog caller needs its actual tokenizer argument count')
        m=self.m;f=self.frame;m.put_u32(f-32,self.records);m.put_u32(f-36,0x8086ff6)
        self.lookup_frame=_catalog_prologue(m,f-36,ebp=f,edi=self.initial['edi'],esi=self.records,ebx=self.initial['ebx'])

    def before_compare(self,index,alias):
        if self.lookup_frame is None:raise ValueError('Comparison precedes its catalog caller')
        # The same argument PUSH executes at all four alias sites; native
        # calls pop their arguments before the next comparison.
        self.m.put_u32(self.lookup_frame-16,self.records);self.comparisons.append((index,alias))

    def catalog_result(self,index,row):
        m=self.m;f=self.frame;m.put_u32(f-8,index)
        if index>=0:
            m.put_u32(f-12,index*2)
            if row[2]<=self.argument_count<=row[3]and row[3]>0:m.put_u32(f-16,index*23)
