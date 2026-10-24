"""Verify that the downloaded source bundle rebuilds its included WASM module."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zig")
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="pyasitic-kernel-source-check-") as directory:
        work=Path(directory)
        with zipfile.ZipFile(ROOT/"dist/native-sources.zip") as archive:
            for name in archive.namelist():
                path=Path(name)
                if path.is_absolute() or ".." in path.parts:raise ValueError("Invalid source archive member")
            archive.extractall(work)
        for source in (ROOT/"native").rglob("*"):
            if source.is_file() and (work/source.relative_to(ROOT)).read_bytes()!=source.read_bytes():raise ValueError(f"Source archive mismatch: {source}")
        compiler=["--zig",args.zig] if args.zig else ["--download-zig"]
        subprocess.run([sys.executable,str(work/"tools/build_kernels.py"),*compiler,"--verify"],check=True)
    print("Downloaded numerical sources rebuild the included module byte for byte")


if __name__=="__main__":main()
