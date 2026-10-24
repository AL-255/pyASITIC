"""Observe raw Pi models/Y/S and resonance returns in complete original CLI sessions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from capture_original_symmetric import ORIGINAL_SHA256, LEGACY_SHA256

ROOT = Path(__file__).resolve().parents[1]
PARENTS = ("network", "network_eddy", "pi_models", "pi_models_eddy", "pix", "gf180_network")
COMMANDS = r'''
set pagination off
set confirm off
set environment TERM dumb
set environment INPUTRC /dev/null
python
import gdb,struct,json
entries={0x8089e40:'model',0x8087d14:'scattering',0x804ec50:'resonance'}
for address in entries:gdb.Breakpoint('*'+hex(address),internal=True)
end
run -g -t process.tek -x input.asit < answers.txt
python
result={};pending={};model_events=[];resonance_events=[];skip_models=0
def memory(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def u32(a):return struct.unpack('<I',memory(a,4))[0]
def ports():return [memory(a,8).hex() for a in (0x80d8da8,0x80d8db0,0x80d8db8,0x80d8dc0,0x80d8dd8,0x80d8de0,0x80d8de8,0x80d8df0)]
control_before=int(gdb.parse_and_eval('$fctrl'))
while len(result)<3:
 address=int(gdb.parse_and_eval('$pc'))
 if address in entries:
  kind=entries[address]
  if kind not in result:
   esp=int(gdb.parse_and_eval('$esp'));pc=u32(esp)
   item=dict(kind=kind)
   if kind=='model':item.update(Y=ports(),frequency_bits=memory(esp+4,8).hex(),coordinate_heights=[memory(u32(0x80d891c)+8*i,8).hex() for i in range(u32(0x80d8904))])
   if kind=='scattering':item['Y']=ports()
   assert pc not in pending
   pending[pc]=item;gdb.Breakpoint('*'+hex(pc),temporary=True,internal=True)
 else:
  assert address in pending,(hex(address),pending)
  item=pending.pop(address);kind=item.pop('kind')
  if kind=='model':item['M']=[memory(0x80d8820+8*i,8).hex() for i in range(12)]
  if kind=='scattering':item['S']=[memory(a,8).hex() for base in (0x80d8d58,0x80d8d28,0x80d8d48,0x80d8d18) for a in (base,base+8)]
  if kind=='resonance':item['extended_bits']=bytes(gdb.parse_and_eval('$st0').bytes).hex()
  if kind=='model':
   model_events.append(item)
   if len(model_events)>skip_models:result[kind]=item
  elif kind=='resonance':
   resonance_events.append(item)
   if len(resonance_events)>skip_models:result[kind]=item
  else:result[kind]=item
 if len(result)<3:gdb.execute('continue',to_string=True)
assert not pending
result.update(control_before=control_before,control_after=int(gdb.parse_and_eval('$fctrl')),model_events=model_events,resonance_events=resonance_events)
open('raw.json','w').write(json.dumps(result))
end
kill
quit
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--library-path", required=True)
    args = parser.parse_args()
    original = args.reference / "run/asitic.linux.2.2"
    legacy = args.reference / "run/libs/libstdc++-2-libc6.1-1-2.9.0.so"
    for path, sha in ((original, ORIGINAL_SHA256), (legacy, LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError(f"Unexpected oracle checksum: {path}")
    records, skipped = [], []
    with tempfile.TemporaryDirectory(prefix="pyasitic-original-pi-sessions-") as directory:
        for name in PARENTS:
            cases = json.loads((ROOT / f"tests/fixtures/{name}.json").read_text())["cases"]
            for index, c in enumerate(cases):
                if c["admittance_matrix"] is None:
                    skipped.append(dict(fixture=name, index=index, reason="Parent fixture has no Y/S record; its explicit failure remains checked separately."))
                    continue
                work = Path(directory) / f"{name}-{index}"
                work.mkdir()
                commands=COMMANDS.replace('skip_models=0','skip_models=1') if c.get('model')=='pi4' else COMMANDS
                for filename, value in (("process.tek", c["technology"]), ("input.asit", c["script"]), ("answers.txt", "quit\n"), ("capture.gdb", commands)):
                    (work / filename).write_text(value)
                env = dict(os.environ, LD_LIBRARY_PATH=args.library_path)
                run = subprocess.run(["gdb", "-q", "-batch", "-x", "capture.gdb", str(original.resolve())], cwd=work, env=env, capture_output=True, text=True, start_new_session=True, timeout=120)
                if run.returncode or not (work / "raw.json").exists():
                    raise RuntimeError(f"Original Pi capture failed {name}/{index}: {run.stdout[-1800:]} {run.stderr[-1000:]}")
                record = json.loads((work / "raw.json").read_text())
                if record["control_before"] != 0x37f or record["control_after"] != 0x37f:
                    raise RuntimeError("Unexpected x87 control word")
                record["repeated_y_identical"] = record["model"]["Y"] == record["scattering"]["Y"]
                action = "pix" if name == "pix" else c.get("model", "pi2")
                request = dict(action=action, **{k: c[k] for k in ("kind", "parameters", "technology", "frequency_hz", "ground", "mesh", "first_pad", "second_pad", "eddy") if k in c})
                record.update(fixture=name, index=index, request=request, script=c["script"])
                records.append(record)
                print(name, index, "raw original Y/Pi/S/resonance captured", flush=True)
    result = dict(reference="Actual original CLI sessions. GDB entry/actual-return breakpoints observe the model-command Pi extractor, resonance helper and first S converter without replacing any numerical/runtime function. First-model Y and later S-conversion Y are recorded separately because repeated commands can have different native histories. Pi4 intermediate and final pad reports are both retained; the selected model is the final de-embedded report. Native model stores are SI; retained resonance returns come directly from ST0.", original_sha256=ORIGINAL_SHA256, legacy_sha256=LEGACY_SHA256, parents={name: hashlib.sha256((ROOT / f"tests/fixtures/{name}.json").read_bytes()).hexdigest() for name in PARENTS}, gdb_commands=COMMANDS, cases=records, skipped=skipped)
    (ROOT / "tests/fixtures/pi_sessions_original.json").write_text(json.dumps(result, separators=(",", ":"), allow_nan=False) + "\n")
    print(len(records), "complete original Pi sessions captured")


if __name__ == "__main__":
    main()
