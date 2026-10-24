"""Strict exponent instruction audit; --raw additionally requires every ST0 bit."""
from fractions import Fraction
import json
import math
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.retained_scalar import Real
from reasitic.x87_math import exp_retained


def operand(words):
    low,high,exponent=words;sig=low|(high<<32);power=exponent&0x7fff;sign=-1 if exponent&0x8000 else 1
    if power==0x7fff:return Real(math.copysign(math.inf,sign)if sig==1<<63 else math.nan)
    if not sig:return Real(math.copysign(0.,sign))
    return Real(Fraction(sign*sig)*Fraction(2)**((power or 1)-16383-63))


def main():
    cases=json.loads((ROOT/'tests/fixtures/exp_original.json').read_text())['cases'];finite=[];raw=[]
    for i,c in enumerate(cases):
        value=exp_retained(operand(c['input_words']));expected=struct.unpack('<d',bytes.fromhex(c['output_bits']))[0]
        if not(math.isnan(float(value))and math.isnan(expected))and struct.pack('<d',float(value)).hex()!=c['output_bits']:finite.append(i)
        target=bytes.fromhex(c['extended_bits']);sig,exponent=struct.unpack('<QH',target)
        actual=struct.pack('<IIH',*value.words())
        if exponent&0x7fff!=0x7fff and actual!=target:raw.append(i)
    print(f'{len(cases)} original exponent instructions: {len(finite)} binary64/class differences; {len(raw)} finite retained differences.')
    if raw:print('Retained differences:',raw)
    raise SystemExit(bool(finite or('--raw'in sys.argv and raw)))


if __name__=='__main__':main()
