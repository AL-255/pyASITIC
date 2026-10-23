"""Generate all GF180 section 3 stacks from a pinned documentation checkout.

Usage: python tools/build_gf180.py --docs /path/to/gf180mcu-pdk
The input directory must contain docs/ and LICENSE. No network during generation.
"""
import argparse
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
REVISION="de3240d7529a6970437ac3344820aaae7839f215"
BASE="https://gf180mcu-pdk.readthedocs.io/en/latest/analog/layout/inter_specs/"
COLORS=("#81b4ef","#f0b567","#8fd1ae","#b899eb","#e5a4b4","#b7c7d4")


def number(value):return format(value,"f").rstrip("0").rstrip(".") if "." in format(value,"f") else format(value,"f")


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--docs",type=Path,required=True)
    args=parser.parse_args();docs=args.docs;spec=docs/"docs/analog/layout/inter_specs"
    destination=ROOT/"src/reasitic/technologies";destination.mkdir(exist_ok=True)
    provenance={}
    paths=list(spec.glob("inter_specs_3*.rst"))+list((spec/"images").glob("2_cross_section_*.png"))+list((spec/"tables_clear").glob("[345]_*.csv"))
    paths += [docs/"docs/analog/spice/elec_specs/tables_clear/5_General_Specification2.csv",
              docs/"docs/physical_verification/design_manual/tables_clear/23_Vian_59.csv",
              docs/"docs/physical_verification/design_manual/tables_clear/06_Drawn_layer10.csv"]
    for path in paths:provenance[path.relative_to(docs).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    with (spec/"tables_clear/5_Sheet_Rho_table.csv").open(newline="") as f:
        sheet={row[0]:Decimal(row[2].split("+/-")[0]) for row in list(csv.reader(f))[1:]}
    catalogue=[]
    for section in range(1,46):
        text=(spec/f"inter_specs_3_{section:02}.rst").read_text();title=text.splitlines()[0]
        count=int(re.search(r"1P(\d)M",title)[1]);top=int(re.search(r"(6|9|11|30)KA",title)[1])
        mim="none" if "without MIM" in title else "B" if "Option B" in title else "A"
        mim_bottom=None if mim=="none" else count-1 if mim=="B" else 2
        identifier=f"gf180-1p{count}m-{top}ka-"+("no-mim" if mim=="none" else f"mim-{mim.lower()}")
        label=f"GF180 · 1P{count}M · {top} kÅ · "+("no MIM" if mim=="none" else f"MIM {mim}")
        # Section 3 diagrams override the inconsistent section 2.1 11KA entry.
        thickness=Decimal({6:"0.7025",9:"1.0025",11:"1.1925",30:"3"}[top])
        passivation=Decimal({6:"1.4025",9:"2.0025",11:"2.3925",30:"3.3"}[top])
        variants={}
        for density in ([None] if mim=="none" else ["1.5","1.0"]):
            sin=Decimal(0) if density is None else Decimal("0.042" if density=="1.5" else "0.062")
            name=identifier+("" if density is None else "-"+density.replace(".","p")+"ff")+".tek"
            heights=[];z=Decimal("0.86")
            for i in range(1,count+1):
                heights.append(z)
                z+=Decimal("1.45" if i==mim_bottom else "1.15")
            oxide_top=heights[-1]+passivation
            metals=[]
            for i,height in enumerate(heights,1):
                metals.append(dict(name=f"M{i}",height=height,thickness=thickness if i==count else Decimal("0.55"),
                                   rsh=sheet[f"TM({top}KA)"] if i==count else sheet[f"M{i}"],color=COLORS[i-1],gds=(34,36,42,46,81,53)[i-1]))
                if i==mim_bottom:metals.append(dict(name="MIM",height=height+Decimal("0.55")+sin,thickness=Decimal("0.295"),rsh=sheet["MIM Top Plate"],color="#dce17d",gds=75))
            index={m["name"]:i for i,m in enumerate(metals)}
            vias=[dict(name=f"VIA{i}",bottom=index[f"M{i}"],top=index[f"M{i+1}"],gds=(35,38,40,41,82)[i-1],space="0.36",overplot="0.12") for i in range(1,count)]
            if mim_bottom:
                vias.append(dict(name="MIMVIA",bottom=index["MIM"],top=index[f"M{mim_bottom+1}"],gds=(35,38,40,41,82)[mim_bottom-1],space="0.5",overplot="0.4"))
            header=["; Copyright 2022 GlobalFoundries PDK Authors. Derived data, Apache-2.0.",
                    "; Converted to ASITIC format by reASITIC. See GF180-NOTICE.txt.",
                    f"; {title}",f"; Source: {BASE}inter_specs_3_{section:02}.html",f"; Upstream revision: {REVISION}",
                    "; Nominal BEOL geometry and sheet R. Substrate 10 ohm-cm / 700 um is ASSUMED.",
                    "; Planar coil model: ILD/IMD/oxide passivation eps=4, nitride passivation eps=7.",
                    "; Local STI/poly/conformal liner and local MIM nitride are not blanket layers.",
                    "; MIM plate geometry is included; CAP is not a calibrated MIM capacitor model.",
                    "; Air 100 um and dielectric rho=1e10 ohm-cm are modeling assumptions.",
                    "; Via spacing 0.36 um covers the published >=4x4-array rule; enclosure 0.12 um.",
                    "; GDS uses GF180 drawn layer numbers. Additional device/marker rules still apply."]
            if top==11:header.append("; 11KA uses drawing t=1.1925 / oxide=2.3925 um; general tables list 1.25 / 2.3.")
            if density:
                header.append(f"; MIM option {mim}: M{mim_bottom}/MIM gap={sin} um, nominal {density} fF/um2 (local nitride eps=7).")
                header.append("; MIMVIA assumes 4.5 ohm/cut; spacing/enclosure are 0.5/0.4 um per MIM rules.")
            lines=header+["", "<chip>","chipx = 512","chipy = 512","fftx = 128","ffty = 128",f"TechFile = {name}","TechPath = .","freq = 2","eddy = 0"]
            for m in metals:lines.append(f"gds_{m['name'].lower()} = {m['gds']}")
            for v in vias:lines.append(f"gds_{v['name'].lower()} = {v['gds']}")
            layers=[("700","10","11.9"),(number(oxide_top),"1e10","4"),("0.3","1e10","7"),("100","1e10","1")]
            for i,(t,rho,eps) in enumerate(layers):lines.extend(["",f"<layer> {i}",f"t = {t}",f"rho = {rho}",f"eps = {eps}"])
            for i,m in enumerate(metals):
                lines.extend(["",f"<metal> {i}",f"name = {m['name']}","layer = 1",f"d = {number(m['height'])}",f"t = {number(m['thickness'])}",f"rsh = {number(m['rsh']*1000)}",f"color = {m['color']}"])
            for i,v in enumerate(vias):
                lines.extend(["",f"<via> {i}",f"name = {v['name']}",f"bottom = {v['bottom']}",f"top = {v['top']}","r = 4.5","width = 0.26",f"space = {v['space']}",f"overplot1 = {v['overplot']}",f"overplot2 = {v['overplot']}"])
            (destination/name).write_text("\n".join(lines)+"\n")
            variants[density or "none"]=name
        catalogue.append(dict(id=identifier,label=label,section=f"3.{section}",routing_metals=count,top_metal_ka=top,
                              top_thickness_um=float(thickness),oxide_passivation_um=float(passivation),mim=mim,mim_bottom=mim_bottom,
                              source=BASE+f"inter_specs_3_{section:02}.html",variants=variants))
    (destination/"catalog.json").write_text(json.dumps(dict(source_revision=REVISION,source_sha256=provenance,presets=catalogue),indent=2)+"\n")
    license_text=(docs/"LICENSE").read_text()
    (destination/"GF180-NOTICE.txt").write_text("GF180MCU technology data\nCopyright 2022 GlobalFoundries PDK Authors\n\nDerived from google/gf180mcu-pdk documentation at revision "+REVISION+".\nConverted to ASITIC .tek format; modeling assumptions and modifications are\nlisted in each file and docs/GF180.md. This is not an RF-qualified PDK model.\n\n"+license_text)
    print(f"Generated {len(catalogue)} documented stacks and {sum(len(p['variants']) for p in catalogue)} .tek files")


if __name__=="__main__":main()
