"""Translate the audited C++ 3D arithmetic into standalone, reviewable Python.

This development tool reads recomp_cpp/src/transformer3d.cpp. The application
executes only the generated Python, with no reference checkout or executable.
Unknown statements fail translation rather than being silently discarded.
"""
import argparse
import hashlib
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BASES = {"endpoints":0,"outer_start":0x44,"outer_end":0x5c,"inner_start":0x88,"inner_end":0xa0}


def expression(text):
    text = re.sub(r"0x[\da-f.]+p[+-]\d+L?",lambda m:f'float.fromhex("{m[0].removesuffix("L")}")',text)
    text = re.sub(r"\b(\d+)\.L\b",r"\1.0",text)
    text = text.replace("*head","head").replace("binary64(","float(").replace("x87::abs(","abs(")
    text = text.replace("number(","_number(").replace("integer(","_integer(")
    text = re.sub(r"technology.metal_heights\[([^]]+)\]",r"technology.metals[\1].geometry_height",text)
    text = re.sub(r"field\(s,(0x[\da-f]+)\)",r"fields[\1]",text)
    text = re.sub(r"s\.(endpoints|outer_start|outer_end|inner_start|inner_end)\[(\d+)\]",
                  lambda m:f"fields[0x{BASES[m[1]]+int(m[2])*8:x}]",text)
    text = text.replace("s.width","fields[0xcc]").replace("s.thickness","fields[0xd4]")
    text = re.sub(r"\badd\(","_add(",text)
    text = re.sub(r"\bsubtract\(","_subtract(",text)
    text = re.sub(r"\bmultiply\(","_multiply(",text)
    text = re.sub(r"\bdivide\(","_divide(",text)
    if any(s in text for s in ("::","->",";","!","history","runtime")):
        raise ValueError(f"Unsupported expression: {text}")
    return text


def translate(lines,kind):
    output = []
    indent = 1
    def emit(line):
        output.append("    "*indent+line)
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("//"):
            if "emission" in line:
                emit("#"+line[2:])
            continue
        if re.fullmatch(r"\[\[maybe_unused\]\] (?:long double|double) \w+;",line):
            continue
        if line.startswith("ConductorSegment s;"):
            emit("fields = {}")
            continue
        if line=="int metal=0;unsigned terminal_index=0;":
            emit("metal = 0")
            continue
        if line.startswith("prepend_geometry_shape(head,"):
            initial = "secondary" if "secondary" in line else "primary"
            emit(f"head = {initial}")
            continue
        if line.startswith("s.width_count=history.winding[1]"):
            continue
        if line=="set_metals(s,metal);prepend_geometry_segment(target.filaments.first,s,runtime);":
            emit("_emit(target,fields,metal)")
            continue
        if line=="prepend_geometry_segment(head->filaments.first,s,runtime.geometry);":
            emit("_emit(head,fields,metal)")
            continue
        if line.startswith("metal=integer(") and line.endswith(";set_metals(s,metal);"):
            emit(expression(line.split(";",1)[0]))
            continue
        if line.startswith("emit_transformer_terminal("):
            match = re.fullmatch(r"emit_transformer_terminal\(\*head,\*head,rounded_210,binary64\((q\d+)\),2\.,(-?1\.),metal,technology,runtime.geometry,.*\);\+\+terminal_index;",line)
            if not match:
                raise ValueError(line)
            emit(f"_terminal(head,head,rounded_210,float({match[1]}),2.0,{match[2]},metal,technology)")
            continue
        if line.startswith("if (") and line.endswith(" {"):
            condition = line[3:-2]
            if condition.startswith("(!(") and condition.endswith("))"):
                condition = "not "+condition[2:-1]
            emit("if "+expression(condition)+":")
            indent += 1
            continue
        if re.fullmatch(r"bool \w+;do \{",line):
            emit("while True:")
            indent += 1
            continue
        match = re.fullmatch(r"}while\((\w+)\);",line)
        if match:
            emit(f"if not {match[1]}:")
            emit("    break")
            indent -= 1
            continue
        if line=="}":
            indent -= 1
            if indent==0:
                continue
            if indent<0:
                raise ValueError("Unbalanced C++ braces")
            continue
        line = re.sub(r"^\[\[maybe_unused\]\] const long double ","",line)
        if not re.fullmatch(r"[\w.\[\](),x0-9]+\s*=.+;",line):
            # Assignments to segment fields contain hexadecimal offsets and
            # array subscripts, transformed by expression() below.
            if "=" not in line or not line.endswith(";"):
                raise ValueError(f"Unsupported statement: {line}")
        emit(expression(line[:-1]))
    if indent!=0:
        raise ValueError(f"Unbalanced function: {kind}, indent {indent}")
    return "\n".join(output)


HEADER = '''"""Generated direct port of the audited ASITIC 3D transformer arithmetic.

Regenerate with tools/port_transformer3d.py. Reference source SHA256:
{sha}
"""
from fractions import Fraction
from .inductance import _round_extended
from .model import Segment


def _add(a,b):
    return _round_extended(Fraction(a)+Fraction(b))


def _subtract(a,b):
    return _round_extended(Fraction(a)-Fraction(b))


def _multiply(a,b):
    return _round_extended(Fraction(a)*Fraction(b))


def _divide(a,b):
    return _round_extended(Fraction(a)/Fraction(b))


def _number(shape,offset):
    return shape.parameters[{{0x68:"metal",0x70:"length",0x78:"height",0x88:"width",0x90:"spacing",0x98:"turns"}}[offset]]


def _integer(shape,offset):
    return int(_number(shape,offset))


def _emit(shape,fields,metal):
    def point(offset):
        return [fields[offset+axis*8] for axis in range(3)]
    shape.segments.insert(0,Segment(point(0),point(0x18),point(0x44),point(0x5c),point(0x88),point(0xa0),
                                   fields[0xcc],fields[0xd4],metal,
                                   primary_width=fields[0x30],primary_thickness=fields[0x38]))


def _terminal(target,args,x,y,clearance,direction,metal,technology):
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference",type=Path,required=True)
    parser.add_argument("--check",action="store_true")
    args = parser.parse_args()
    source = (args.reference/"recomp_cpp/src/transformer3d.cpp").read_text()
    terminal_start = source.index("    ConductorSegment s;",source.index("void emit_transformer_terminal("))
    main_start = source.index("void build_3d_transformer(")
    body_start = source.index("    prepend_geometry_shape(head,",main_start)
    output = HEADER.format(sha=hashlib.sha256(source.encode()).hexdigest())
    output += translate(source[terminal_start:main_start].splitlines(),"terminal")
    output += "\n\n\ndef build_3d(primary,secondary,technology):\n"
    output += translate(source[body_start:source.rfind("}")].splitlines(),"builder")
    output += "\n    return [primary,secondary]\n"
    compile(output,"transformer3d.py","exec")
    destination = ROOT/"src/reasitic/transformer3d.py"
    if args.check:
        if destination.read_text()!=output:
            raise SystemExit("Generated Python differs")
        print("3D port matches the audited reference source")
    else:
        destination.write_text(output)
        print(destination)


if __name__=="__main__":
    main()
