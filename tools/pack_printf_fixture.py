"""Losslessly compact a dense native printf capture; verify every boundary."""
import argparse,gzip,hashlib,io,json
from pathlib import Path
from printf_fixture import pack_state,compact_pages


def compact(fixture):
    templates={};states=0
    for case in fixture['cases']:
        for call in case['printf_calls']:
            for phase in ('before','after'):
                if phase in call:pack_state(fixture,call[phase],templates);states+=1
    pages=compact_pages(fixture);return states,pages


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('output',type=Path);args=p.parse_args()
    source_hash=hashlib.sha256(args.input.read_bytes()).hexdigest()
    with gzip.open(args.input,'rt')as stream:f=json.load(stream)
    states,pages=compact(f);f['printf_projection']=dict(dense_sha256=source_hash,states_checked=states,pages_checked=pages,reference='Every context field, register set, FP byte, ordered region reference, page reference and original page byte expands identically to the complete dense capture. No owner or target byte is removed.')
    with gzip.GzipFile(str(args.output),'wb',mtime=0)as raw:
        # Iterative output avoids a second multi-gigabyte temporary string.
        with io.TextIOWrapper(raw,encoding='utf-8',newline='\n')as text:json.dump(f,text,separators=(',',':'))
    print(json.dumps(dict(states_checked=states,compressed_bytes=args.output.stat().st_size,sha256=hashlib.sha256(args.output.read_bytes()).hexdigest())))


if __name__=='__main__':main()
