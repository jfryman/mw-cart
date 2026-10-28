#!/usr/bin/env python3
"""Rebuild mw-cart fabrication + documentation assets with kicad-cli (KiCad 8+).

Mirrors the layout of the upstream KiBot output (Doc/, Fab/) for the parts that
kicad-cli can produce.  KiBot-only extras (Browse/ HTML, iBoM, boardview) are not made.
Runs on Linux and macOS (not Windows).

Usage: python3 -I tools/build_outputs.py <mw-cart dir> <output dir>   (output dir is wiped)

kicad-cli is found in this order: $KICAD_CLI, `kicad-cli` on PATH (Arch/Omarchy `kicad`
package, Homebrew), /Applications/KiCad/KiCad.app, then the org.kicad.KiCad flatpak.
The PCB references ${KICAD8_3DMODEL_DIR} and ${KICAD8_3RD_PARTY}. Both default sensibly:
the stock 3D library of whichever KiCad was found, and tools/ext/3rdparty (run
tools/fetch-ext.sh once). Override either with the environment variable. STEP and renders
are skipped if the 3D library directory doesn't exist.
"""
import csv, io, os, re, shutil, subprocess, sys, zipfile

SRC, OUT = (os.path.abspath(p) for p in sys.argv[1:3])
NAME = "mega-wifi"
PCB, SCH = f"{SRC}/{NAME}.kicad_pcb", f"{SRC}/{NAME}.kicad_sch"
LAYERS = ["F.Cu", "B.Cu", "F.Paste", "F.Silkscreen", "F.Mask", "B.Mask", "Edge.Cuts", "F.Fab"]
# KiBot JLCPCB rotation fixes (regex on footprint name -> degrees added), as seen in Rev.B CPL
JLC_ROT = [(r"^SOT-223", 180), (r"^SOT-23", 180), (r"^TSSOP-", -90)]
MAC_APP = "/Applications/KiCad/KiCad.app/Contents"
HERE = os.path.dirname(os.path.abspath(__file__))


def find_kicad():
    """(argv prefix for kicad-cli, default 3D model dir, is_flatpak)"""
    cli = os.environ.get("KICAD_CLI") or shutil.which("kicad-cli")
    if not cli and os.path.exists(f"{MAC_APP}/MacOS/kicad-cli"):
        cli = f"{MAC_APP}/MacOS/kicad-cli"
    if cli:
        real = os.path.realpath(cli)
        if ".app/Contents/" in real:
            models = real.split(".app/Contents/")[0] + ".app/Contents/SharedSupport/3dmodels"
        else:
            models = next((m for m in ("/usr/share/kicad/3dmodels", "/usr/local/share/kicad/3dmodels")
                           if os.path.isdir(m)), "/usr/share/kicad/3dmodels")
        return [cli], models, False
    if shutil.which("flatpak") and subprocess.run(["flatpak", "info", "org.kicad.KiCad"],
                                                  capture_output=True).returncode == 0:
        return ["flatpak", "run", "--command=kicad-cli", "org.kicad.KiCad"], "/app/extensions/Library/3dmodels", True
    sys.exit("kicad-cli not found: install KiCad (pacman -S kicad / brew install --cask kicad / "
             "flatpak org.kicad.KiCad) or set KICAD_CLI")


KICAD, MODELS_DEFAULT, FLATPAK = find_kicad()
ENV = {
    "KICAD8_3DMODEL_DIR": os.environ.get("KICAD8_3DMODEL_DIR") or MODELS_DEFAULT,
    "KICAD8_3RD_PARTY": os.environ.get("KICAD8_3RD_PARTY") or os.path.join(HERE, "ext", "3rdparty"),
}
HAVE_3D = FLATPAK or os.path.isdir(ENV["KICAD8_3DMODEL_DIR"])


def kc(*args):
    if FLATPAK:
        extra = [f"--filesystem={SRC}", f"--filesystem={OUT}"]
        for k, v in ENV.items():
            extra.append(f"--env={k}={v}")
            if not v.startswith("/app/"):
                extra.append(f"--filesystem={v}:ro")
        cmd = KICAD[:2] + extra + KICAD[2:] + list(args)
        env = None
    else:
        cmd = KICAD + list(args)
        env = {**os.environ, **ENV}
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
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
    if HAVE_3D:
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
