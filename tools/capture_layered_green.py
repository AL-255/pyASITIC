"""Capture intact original Green routines, bundled complex DSO and native trig."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import subprocess
import tempfile

from capture_original_symmetric import ORIGINAL_SHA256, LEGACY_SHA256

ROOT = Path(__file__).resolve().parents[1]


def cases():
    rows = []
    for c in json.loads((ROOT / "tests/fixtures/green.json").read_text())["cases"]:
        values = [c[k] for k in ("k", "frequency", "layer1", "layer2", "depth", "height", "separation")]
        rows.extend(dict(mode=mode, input=values + [0.]) for mode in (0, 1, 3, 4, 5, 6, 7))
    rng = random.Random(943268)
    values = [0., -0., 1e-320, -1e-320, 1e-100, -1e-100, .1, -.1, 1., -1., 4., -4., 710., -710., 11400., -11400., math.inf, -math.inf, math.nan]
    for real in values:
        for imag in (0., -0., .1, -1., 10., 1e8, 1e18, 2.**63, math.inf, math.nan):
            rows.extend(dict(mode=mode, input=[real, imag, 0., 0., 0., 0., 0., 0.]) for mode in (2, 8, 9, 10, 11))
    for _ in range(256):
        real, imag = rng.uniform(-1000., 1000.), rng.uniform(-1e6, 1e6)
        rows.extend(dict(mode=mode, input=[real, imag, 0., 0., 0., 0., 0., 0.]) for mode in (2, 8, 9, 10, 11))
    angles = [0., -0., 1e-320, -1e-320, math.inf, -math.inf, math.nan]
    for x in (4., math.pi * 2, 1e3, 1e8, 1e15, 1e18, 2.**63):
        for v in (math.nextafter(x, 0.), x, math.nextafter(x, math.inf)):
            angles.extend((v, -v))
    angles.extend(math.ldexp(rng.uniform(.5, 1.), rng.randint(3, 63)) * rng.choice([-1, 1]) for _ in range(1024))
    for x in angles:
        rows.extend(dict(mode=mode, input=[x, 1., 0., 0., 0., 0., 0., 0.]) for mode in (12, 13))
    for _ in range(256):
        x, y = rng.uniform(-1e6, 1e6), rng.uniform(-1e6, 1e6)
        rows.extend(dict(mode=mode, input=[x, y, 0., 0., 0., 0., 0., 3.]) for mode in (12, 13))
    return rows


def number(value):
    return value if math.isfinite(value) else "nan" if math.isnan(value) else "inf" if value > 0 else "-inf"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    args = parser.parse_args()
    original = args.reference / "run/asitic.linux.2.2"
    legacy = args.reference / "run/libs/libstdc++-2-libc6.1-1-2.9.0.so"
    for path, sha in ((original, ORIGINAL_SHA256), (legacy, LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError(f"Unexpected oracle checksum: {path}")
    rows = cases()
    source = ROOT / "tools/original_green_probe.cpp"
    flags = ["-m32", "-O2", "-mfpmath=sse", "-msse2", "-ffp-contract=off", "-fno-pie", "-fno-pic", "-fno-stack-protector", "-fno-exceptions", "-fno-rtti", "-nostdlib", "-no-pie", "-Wl,-Ttext-segment=0x10000000"]
    with tempfile.TemporaryDirectory(prefix="pyasitic-original-green-") as directory:
        work = Path(directory)
        binary, payload = work / "probe", work / "input.bin"
        subprocess.run(["g++", *flags, str(source), "/lib/i386-linux-gnu/libc.so.6", "-Wl,--dynamic-linker=/lib/ld-linux.so.2", "-o", str(binary)], check=True)
        payload.write_bytes(struct.pack("<I", len(rows)) + b"".join(struct.pack("<I8d", row["mode"], *row["input"]) for row in rows))
        run = subprocess.run([str(binary), str(original.resolve()), str(legacy.resolve()), str(payload)], capture_output=True, start_new_session=True, timeout=120)
        if run.returncode or len(run.stdout) != 4 + 26 * len(rows):
            raise RuntimeError(f"Original Green probe failed {run.returncode}: {len(run.stdout)} bytes, {run.stderr[:300]}")
    before = struct.unpack_from("<H", run.stdout)[0]
    after = struct.unpack_from("<H", run.stdout, len(run.stdout) - 2)[0]
    if before != after or before & 0xf00 != 0x300:
        raise RuntimeError(f"Unexpected x87 control word {before:#x}/{after:#x}")
    for i, row in enumerate(rows):
        raw = run.stdout[2 + 26 * i:2 + 26 * (i + 1)]
        row["input"] = [number(v) for v in row["input"]]
        row.update(output_bits=raw[:16].hex(), extended_bits=raw[16:].hex())
    cpu = {}
    for line in Path("/proc/cpuinfo").read_text().split("\n\n", 1)[0].splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() in ("vendor_id", "cpu family", "model", "model name", "stepping"):
            cpu[key.strip()] = value.strip()
    result = dict(reference="Modes 0–7 call intact original ASITIC Green entry points; modes 8–11 call intact bundled legacy complex DSO entry points. Modes 12–13 separately execute native FCOS/FSIN instructions, including retained products; these are instruction oracles, not ASITIC entry points.", original_sha256=ORIGINAL_SHA256, legacy_sha256=LEGACY_SHA256, native_instruction_environment=dict(cpu=cpu, control_word_before=before, control_word_after=after), probe_source=source.read_text(), compile_flags=flags, cases=rows)
    output = ROOT / "tests/fixtures/layered_green_original.json"
    output.write_text(json.dumps(result, separators=(",", ":"), allow_nan=False) + "\n")
    print(len(rows), "original Green/legacy complex/native trig cases captured")


if __name__ == "__main__":
    main()
