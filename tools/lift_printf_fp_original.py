"""Translate the pinned formatter's instruction listing into source operations.

This is an offline source-generation step. The browser never opens a native
binary, disassembles code, or loads captured output/state to execute it.
"""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LIBC_SHA256='e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0'
RANGES=[(0x50620,0x51fe0,'mpn'),(0x57850,0x579d0,'grouping'),(0x58230,0x58570,'buffer'),
        (0x58810,0x5ab70,'decimal'),(0x60788,0x608a0,'argument'),(0x60a10,0x60a90,'long-double-argument'),
        (0x617c8,0x617e0,'decimal-call'),(0x88510,0x8854c,'alloca-cutoff'),(0xbbc10,0xbbc53,'memset'),
        (0x61f3b,0x61f49,'mode-flags'),
        (0x17d579,0x17d595,'pc-thunks')]


def lift(libc):
    if hashlib.sha256(libc.read_bytes()).hexdigest()!=LIBC_SHA256:raise ValueError('Unrecognized libc build')
    instructions=[];texts=[]
    for start,end,name in RANGES:
        command=['objdump','-d','-Mintel','--insn-width=16','--start-address='+hex(start),'--stop-address='+hex(end),str(libc)]
        output=subprocess.check_output(command,env=dict(PATH=os.defpath,LANG='C',LC_ALL='C'),text=True)
        for line in output.splitlines():
            match=re.fullmatch(r'\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} )*[0-9a-f]{2})\s+(.+)',line)
            if not match:continue
            address=int(match[1],16);raw=bytes.fromhex(match[2]);text=match[3].split('#',1)[0].strip()
            if address+len(raw)>end:raise ValueError('Source range ends inside an instruction')
            parts=text.split(None,1);opcode=parts[0];arguments=parts[1]if len(parts)>1 else''
            if opcode in('cs','ds','es','data16'):
                parts=arguments.split(None,1);opcode=parts[0];arguments=parts[1]if len(parts)>1 else''
            if opcode in('call','jmp')or opcode.startswith('j'):
                arguments=arguments.split(' <',1)[0]
            instructions.append([address,len(raw),opcode,arguments,raw.hex()]);texts.append(f'{address:x}: {text}')
    return dict(license='GNU LGPL-2.1-or-later; original glibc code Copyright Free Software Foundation, Inc.; see GLIBC-LGPL-2.1.txt',libc_sha256=LIBC_SHA256,ranges=[list(r)for r in RANGES],instructions=instructions)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--libc',type=Path,default=Path('/lib/i386-linux-gnu/libc.so.6'));p.add_argument('--output',type=Path,default=ROOT/'src/reasitic/printf_fp_program.json');p.add_argument('--verify',action='store_true');args=p.parse_args()
    source=(json.dumps(lift(args.libc),separators=(',',':'))+'\n').encode()
    if args.verify:
        if args.output.read_bytes()!=source:raise ValueError('Generated formatter source differs')
    else:args.output.write_bytes(source)
    print(len(json.loads(source)['instructions']),'source instructions;',len(source),'bytes;',hashlib.sha256(source).hexdigest())


if __name__=='__main__':main()
