"""Rebuild the browser's retained-precision kernels with pinned Zig 0.13.0."""
import argparse
import hashlib
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
ZIG_URL="https://ziglang.org/download/0.13.0/zig-linux-x86_64-0.13.0.tar.xz"
ZIG_SHA256="d45312e61ebcc48032b77bc4cf7fd6915c11fa16e4aad116b66c9468211230ea"


def download_zig():
    if platform.system()!="Linux" or platform.machine()!="x86_64":
        raise RuntimeError("Automatic compiler download supports Linux x86_64; supply --zig on other hosts")
    directory=Path(tempfile.gettempdir())/"pyasitic-zig-0.13.0"
    directory.mkdir(exist_ok=True)
    archive=directory/"zig.tar.xz"
    if not archive.exists():urllib.request.urlretrieve(ZIG_URL,archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=ZIG_SHA256:
        raise RuntimeError("Zig archive checksum mismatch")
    binary=directory/"zig-linux-x86_64-0.13.0/zig"
    if not binary.exists():
        with tarfile.open(archive) as source:
            source.extractall(directory,filter="data")
    return str(binary)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zig",help="Path to Zig 0.13.0")
    parser.add_argument("--download-zig",action="store_true",help="Download and verify the pinned compiler in /tmp")
    parser.add_argument("--output",type=Path,default=ROOT/"web/numeric.wasm")
    parser.add_argument("--verify",action="store_true",help="Compare a rebuild against the checked-in browser module")
    args=parser.parse_args()
    zig=args.zig or (download_zig() if args.download_zig else shutil.which("zig"))
    if not zig:parser.error("Supply --zig or --download-zig")
    if subprocess.check_output([zig,"version"],text=True).strip()!="0.13.0":
        parser.error("The reproducible kernel build requires Zig 0.13.0")
    vendor=ROOT/"native/softfloat"
    command=[zig,"cc","-target","wasm32-freestanding","-O3","-g0","-s","-fno-builtin","-fno-exceptions","-fno-rtti",
             "-DSOFTFLOAT_FAST_INT64","-DINLINE_LEVEL=5","-DSOFTFLOAT_ROUND_ODD",
             "-I"+str(ROOT/"native"),"-I"+str(vendor/"include"),"-I"+str(vendor/"8086"),
             str(ROOT/"native/fft.c"),*[str(p) for p in sorted((ROOT/"native").glob("*.cpp"))],
             *[str(p) for p in sorted(vendor.rglob("*.c"))],
             "-nostdlib","-Wl,--no-entry","-Wl,--export-memory"]
    with tempfile.TemporaryDirectory(prefix="pyasitic-kernel-build-") as directory:
        output=Path(directory)/"numeric.wasm"
        subprocess.run([*command,"-o",str(output)],check=True)
        data=output.read_bytes()
    if args.verify:
        if data!=args.output.read_bytes():raise RuntimeError("Compiled module differs from the checked-in artifact")
    else:args.output.write_bytes(data)
    print(f"{'Verified' if args.verify else 'Built'} {args.output}: {len(data)} bytes, SHA256 {hashlib.sha256(data).hexdigest()}")


if __name__=="__main__":main()
