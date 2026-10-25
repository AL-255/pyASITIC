"""Split a complete compact native capture without changing an archive byte."""
import argparse,json
from pathlib import Path
from printf_archive import read_fixture,split_archive


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('manifest',type=Path);args=p.parse_args()
    f=read_fixture(args.input);histories=len(f['cases']);parents=f['parents'];del f
    manifest=split_archive(args.input,args.manifest,histories=histories,parents=parents)
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
