"""Bundled, documented ASITIC process presets, available offline in Pyodide."""
import json
from functools import lru_cache
from pathlib import Path
from .technology import Technology

DIRECTORY=Path(__file__).with_name("technologies")


@lru_cache(maxsize=1)
def catalogue():
    return json.loads((DIRECTORY/"catalog.json").read_text())["presets"]


def list_presets():
    return [dict(id="sample-cmos",label="Sample CMOS · 5 metals",routing_metals=5,mim="none")]+catalogue()


def identify(technology):
    filename=technology.chip.get("techfile","")
    for preset in catalogue():
        for density,path in preset["variants"].items():
            if filename==path:return dict(preset,density=density)
    return None


def load_preset(identifier,density="1.5",*,substrate_rho=10,substrate_thickness=700):
    if identifier=="sample-cmos":return Path(__file__).with_name("CMOS.tek").read_text()
    preset=next((p for p in catalogue() if p["id"]==identifier),None)
    if preset is None:raise ValueError("Unknown technology preset")
    key="none" if preset["mim"]=="none" else str(float(density))
    if key not in preset["variants"]:raise ValueError("MIM density must be 1.0 or 1.5 fF/um2")
    if not 0<substrate_rho<1e12 or not 0<substrate_thickness<1e6:raise ValueError("Substrate resistivity and thickness must be finite and positive")
    text=(DIRECTORY/preset["variants"][key]).read_text()
    # Only the documented, assumed bulk parameters are adjustable here.
    text=text.replace("<layer> 0\nt = 700\nrho = 10\n",f"<layer> 0\nt = {substrate_thickness:g}\nrho = {substrate_rho:g}\n")
    text=text.replace("Substrate 10 ohm-cm / 700 um is ASSUMED.",f"Substrate {substrate_rho:g} ohm-cm / {substrate_thickness:g} um is ASSUMED.")
    Technology.from_text(text)
    return text
