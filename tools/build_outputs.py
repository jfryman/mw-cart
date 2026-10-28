#!/usr/bin/env python3
"""Rebuild mw-cart fabrication + documentation assets with kicad-cli (KiCad flatpak).

Mirrors the layout of the upstream KiBot output (Doc/, Fab/) for the parts that
kicad-cli can produce.  KiBot-only extras (Browse/ HTML, iBoM, boardview) are not made.

Usage: python3 -I tools/build_outputs.py <mw-cart dir> <output dir>
Env:   KICAD8_3DMODEL_DIR / KICAD8_3RD_PARTY are forwarded into the flatpak if set; 3D outputs
       (STEP, renders) are only built when KICAD8_3DMODEL_DIR is set.  Typical:
         KICAD8_3DMODEL_DIR=/app/extensions/Library/3dmodels \
         KICAD8_3RD_PARTY=$PWD/tools/ext/3rdparty python3 -I tools/build_outputs.py mw-cart build/rev-c
"""
import csv, io, os, re, shutil, subprocess, sys, zipfile

SRC, OUT = (os.path.abspath(p) for p in sys.argv[1:3])
NAME = "mega-wifi"
PCB, SCH = f"{SRC}/{NAME}.kicad_pcb", f"{SRC}/{NAME}.kicad_sch"
LAYERS = ["F.Cu", "B.Cu", "F.Paste", "F.Silkscreen", "F.Mask", "B.Mask", "Edge.Cuts", "F.Fab"]
# KiBot JLCPCB rotation fixes (regex on footprint name -> degrees added), as seen in Rev.B CPL
JLC_ROT = [(r"^SOT-223", 180), (r"^SOT-23", 180), (r"^TSSOP-", -90)]


def kc(*args):
    env = []
    for var in ("KICAD8_3DMODEL_DIR", "KICAD8_3RD_PARTY"):
        if os.environ.get(var):
            env.append(f"--env={var}={os.environ[var]}")
            if not os.environ[var].startswith("/app/"):
                env.append(f"--filesystem={os.environ[var]}:ro")
    cmd = ["flatpak", "run", f"--filesystem={SRC}", f"--filesystem={OUT}", *env,
           "--command=kicad-cli", "org.kicad.KiCad", *args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"kicad-cli failed: {' '.join(args)}\n{r.stdout}\n{r.stderr}")
    return r.stdout


def d(*parts):
    p = os.path.join(OUT, *parts)
    os.makedirs(p, exist_ok=True)
    return p


def bom_rows():
    """Grouped BOM straight from the schematic (in_bom, not DNP)."""
    tmp = os.path.join(d("Fab", "BoM", "Generic"), "_raw.csv")
    kc("sch", "export", "bom", "-o", tmp, "--exclude-dnp",
       "--fields", "Reference,Value,Footprint,${QUANTITY},LCSC#,manf#,Datasheet,Description",
       "--labels", "Refs,Value,Footprint,Qty,LCSC,MPN,Datasheet,Description",
       "--group-by", "Value,Footprint,LCSC#", "--ref-range-delimiter", "", SCH)
    rows = list(csv.DictReader(open(tmp, encoding="utf-8")))
    os.remove(tmp)
    for r in rows:
        r["Footprint"] = r["Footprint"].split(":")[-1]
        r["Refs"] = " ".join(sorted(re.split(r"[ ,]+", r["Refs"].strip()),
                                    key=lambda x: (re.sub(r"\d", "", x), int(re.sub(r"\D", "", x) or 0))))
    return rows


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    # ---- documentation
    kc("sch", "export", "pdf", "-o", f"{d('Doc', 'Schematic')}/{NAME}-schematic.pdf", SCH)
    kc("sch", "export", "netlist", "--format", "kicadsexpr", "-o", f"{d('Doc', 'Export')}/{NAME}-netlist.net", SCH)
    kc("pcb", "export", "ipcd356", "-o", f"{d('Doc', 'Export')}/{NAME}-IPC-D-356.d356", PCB)
    for ly in LAYERS:
        kc("pcb", "export", "pdf", "-l", f"{ly},Edge.Cuts" if ly != "Edge.Cuts" else ly,
           "--mode-single", "-o", f"{d('Doc', 'PCB', 'PDF')}/{NAME}-{ly.replace('.', '_')}.pdf", PCB)
    kc("pcb", "export", "pdf", "-l", "F.Fab,F.Silkscreen,Edge.Cuts", "--mode-single", "--ibt",
       "-o", f"{d('Doc', 'PCB', 'PDF')}/{NAME}-assembly.pdf", PCB)
    if os.environ.get("KICAD8_3DMODEL_DIR"):
        kc("pcb", "export", "step", "--subst-models", "-f", "-o", f"{d('Doc', '3D')}/{NAME}-3D.step", PCB)
        for side in ("top", "bottom"):
            kc("pcb", "render", "--side", side, "--quality", "high", "-w", "1600", "--height", "1000",
               "-o", f"{d('Doc', 'PCB', '2D_render')}/{NAME}-{side}.png", PCB)
        kc("pcb", "render", "--side", "top", "--rotate", "-30,0,0", "--quality", "high", "-w", "1600",
           "--height", "1000", "-o", f"{d('Doc', '3D')}/{NAME}-3D_top30deg.png", PCB)

    # ---- generic fab
    g = d("Fab", "Gerbers")
    kc("pcb", "export", "gerbers", "--no-protel-ext", "--subtract-soldermask", "-l", ",".join(LAYERS), "-o", g, PCB)
    kc("pcb", "export", "drill", "--generate-map", "--map-format", "pdf", "-o", g + "/", PCB)
    pos = d("Fab", "Position")
    kc("pcb", "export", "pos", "--side", "both", "--format", "csv", "--units", "mm",
       "--use-drill-file-origin", "-o", f"{pos}/{NAME}-both_pos.csv", PCB)
    kc("pcb", "export", "pos", "--side", "both", "--format", "ascii", "--units", "mm",
       "--use-drill-file-origin", "-o", f"{pos}/{NAME}-both_pos.pos", PCB)

    rows = bom_rows()
    with open(f"{d('Fab', 'BoM', 'Generic')}/{NAME}-bom.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Row", "Description", "References", "Value", "Footprint", "Quantity Per PCB",
                    "Datasheet", "manf#", "LCSC#"])
        for i, r in enumerate(rows, 1):
            w.writerow([i, r["Description"], r["Refs"], r["Value"], r["Footprint"], r["Qty"],
                        r["Datasheet"], r["MPN"], r["LCSC"]])

    # ---- JLCPCB
    j = d("Fab", "Manufacturers", "JLCPCB")
    kc("pcb", "export", "gerbers", "--subtract-soldermask", "-l", ",".join(LAYERS), "-o", j, PCB)
    kc("pcb", "export", "drill", "--excellon-separate-th", "--generate-map", "--map-format", "gerberx2",
       "-o", j + "/", PCB)
    with open(f"{j}/{NAME}_bom_jlc.csv", "w", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for r in rows:
            if r["LCSC"]:
                w.writerow([r["Value"], r["Refs"].replace(" ", ","), r["Footprint"], r["LCSC"]])
    jlc_refs = {ref for r in rows if r["LCSC"] for ref in r["Refs"].split()}
    with open(f"{pos}/{NAME}-both_pos.csv") as f_in, open(f"{j}/{NAME}_cpl_jlc.csv", "w") as f_out:
        f_out.write("Designator,Val,Package,Mid X,Mid Y,Rotation,Layer\n")
        for r in csv.DictReader(f_in):
            if r["Ref"] not in jlc_refs:
                continue
            rot = float(r["Rot"]) + sum(a for pat, a in JLC_ROT if re.match(pat, r["Package"]))
            f_out.write(f'"{r["Ref"]}","{r["Val"]}","{r["Package"]}",{float(r["PosX"]):.4f},'
                        f'{float(r["PosY"]):.4f},{rot % 360:.4f},{r["Side"]}\n')
    with zipfile.ZipFile(f"{d('Fab', 'Manufacturers')}/{NAME}-JLCPCB.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(os.listdir(j)):
            z.write(os.path.join(j, fn), fn)
    print(kc("pcb", "export", "stats", "--format", "report", "-o", f"{OUT}/{NAME}-stats.txt", PCB) or "done")


if __name__ == "__main__":
    main()
