"""Swap U7 SC16C550BIBS -> TL16C550DRHB on mw-cart Rev.B (text-level, keeps KiCad 8 format).

Usage: python3 apply_tl16c550d.py <mw-cart dir>
"""
import re, sys, uuid

root = sys.argv[1]
U = lambda: str(uuid.uuid4())
ROOT_SHEET = "8beda605-69f4-4c50-a2e5-833bea0e207c"
WIFI_SHEET = "00000000-0000-0000-0000-00005619415c"
NEW_FP = "Package_DFN_QFN:Texas_RHB0032E_VQFN-32-1EP_5x5mm_P0.5mm_EP3.45x3.45mm"
DS = "https://www.ti.com/lit/ds/symlink/tl16c550d.pdf"
DESC = "UART (ACE) with 16-byte FIFOs and autoflow control, VQFN-32 RHB"
PIN_RENAME = {"6": "SIN", "7": "SOUT", "8": "~{CS2}", "9": "NC", "10": "XIN", "11": "XOUT",
              "12": "~{WR1}", "14": "~{RD1}", "20": "INTRPT", "23": "MR"}


def block(text, start):
    """Return end index (exclusive) of the s-expression starting at text[start] == '('."""
    depth, i, instr = 0, start, False
    while True:
        c = text[i]
        if instr:
            if c == '\\': i += 1
            elif c == '"': instr = False
        elif c == '"': instr = True
        elif c == '(': depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0: return i + 1
        i += 1


def sub1(pat, rep, s, flags=0):
    out, n = re.subn(pat, rep, s, count=1, flags=flags)
    assert n == 1, f"pattern not found: {pat}"
    return out


def edit_block(text, anchor, fn):
    """Find the enclosing top-level-ish block whose header line matches anchor and apply fn."""
    i = text.index(anchor)
    j = block(text, i)
    return text[:i] + fn(text[i:j]) + text[j:]


def enclosing_symbol(text, needle):
    k = text.index(needle)
    i = text.rindex("\n\t(symbol\n", 0, k) + 1
    return i, block(text, i)


def prop(name, value, at, hide=True, size="1.27 1.27", indent="\t\t"):
    h = f"\n{indent}\t\t(hide yes)" if hide else ""
    return (f'{indent}(property "{name}" "{value}"\n{indent}\t(at {at})\n{indent}\t(effects\n'
            f'{indent}\t\t(font\n{indent}\t\t\t(size {size})\n{indent}\t\t){h}\n{indent}\t)\n{indent})\n')


# ---------------------------------------------------------------- schematic
sch_path = f"{root}/wifi.kicad_sch"
sch = open(sch_path).read()


def fix_lib(b):
    b = b.replace('"doragasu:SC16C550BIBS"', '"mw-cart:TL16C550DRHB"')
    b = b.replace('"SC16C550BIBS_', '"TL16C550DRHB_')
    b = b.replace('(property "Value" "SC16C550BIBS"', '(property "Value" "TL16C550DRHB"')
    b = b.replace("Package_DFN_QFN:HVQFN-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm", NEW_FP)
    b = b.replace("https://www.nxp.com/docs/en/data-sheet/SC16C550B.pdf", DS)
    b = b.replace('"Parallel to UART"', f'"{DESC}"')

    def pin(m):
        p = m.group(0)
        num = re.search(r'\(number "([^"]+)"', p).group(1)
        if num in PIN_RENAME:
            p = re.sub(r'\(name "[^"]*"', f'(name "{PIN_RENAME[num]}"', p, count=1)
        if num == "9":
            p = p.replace("(pin power_in", "(pin passive", 1)
        return p
    return re.sub(r'\(pin \w+ \w+.*?\(number "[^"]+"', pin, b, flags=re.S)


sch = edit_block(sch, '(symbol "doragasu:SC16C550BIBS"', fix_lib)

# U7 instance
i, j = enclosing_symbol(sch, '(lib_id "doragasu:SC16C550BIBS")')
b = sch[i:j]
b = b.replace('(lib_id "doragasu:SC16C550BIBS")', '(lib_id "mw-cart:TL16C550DRHB")')
b = b.replace('(property "Value" "SC16C550BIBS"', '(property "Value" "TL16C550DRHB"')
b = b.replace("Package_DFN_QFN:HVQFN-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm", NEW_FP)
b = b.replace("https://www.nxp.com/docs/en/data-sheet/SC16C550B.pdf", DS)
b = b.replace('"Parallel to UART"', f'"{DESC}"')
b = b.replace('(property "LCSC#" "C3310482"', '(property "LCSC#" "C2653239"')
b = sub1(r'(\t\t\(pin "21"\n)', prop("manf#", "TL16C550DRHBR", "81.28 85.09 0") + r"\1", b)
sch = sch[:i] + b + sch[j:]

# Y1 -> 20 MHz (same 12 pF load), lift ref/value text clear of the new XIN label
i, j = enclosing_symbol(sch, '(property "Reference" "Y1"')
b = sch[i:j]
b = b.replace('(property "Value" "24 MHz"\n\t\t\t(at 102.87 101.6 90)', '(property "Value" "20 MHz"\n\t\t\t(at 102.87 99.06 90)')
b = b.replace('(property "Reference" "Y1"\n\t\t\t(at 102.87 99.06 90)', '(property "Reference" "Y1"\n\t\t\t(at 102.87 96.52 90)')
b = b.replace('(property "LCSC#" "C2901723"', '(property "LCSC#" "C252261"')
b = b.replace("\t\t(fields_autoplaced yes)\n", "")
b = sub1(r'(\t\t\(pin "1"\n)', prop("manf#", "7E20000E12UCG", "102.87 105.41 0") + r"\1", b)
sch = sch[:i] + b + sch[j:]

# RI (pin 27): drop no-connect, tie to VCC
sch = sub1(r'\t\(no_connect\n\t\t\(at 99\.06 87\.63\)\n\t\t\(uuid "[^"]+"\)\n\t\)\n', "", sch)


def wire(x1, y1, x2, y2):
    return (f"\t(wire\n\t\t(pts\n\t\t\t(xy {x1} {y1}) (xy {x2} {y2})\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n"
            f"\t\t\t(type default)\n\t\t)\n\t\t(uuid \"{U()}\")\n\t)\n")


def label(name, x, y, ang):
    just = "left bottom" if ang == 0 else "right bottom"
    return (f'\t(label "{name}"\n\t\t(at {x} {y} {ang})\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.524 1.524)\n'
            f'\t\t\t)\n\t\t\t(justify {just})\n\t\t)\n\t\t(uuid "{U()}")\n\t)\n')


def instances(ref):
    return (f'\t\t(instances\n\t\t\t(project "mega-wifi"\n\t\t\t\t(path "/{ROOT_SHEET}/{WIFI_SHEET}"\n'
            f'\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n')


vcc_ref = "#PWR041"
vcc = (f'\t(symbol\n\t\t(lib_id "power:VCC")\n\t\t(at 101.6 87.63 270)\n\t\t(unit 1)\n\t\t(exclude_from_sim no)\n'
       f'\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n\t\t(uuid "{U()}")\n'
       + prop("Reference", vcc_ref, "105.41 87.63 0")
       + prop("Value", "VCC", "105.41 87.63 0", hide=False)
       + prop("Footprint", "", "101.6 87.63 0") + prop("Datasheet", "", "101.6 87.63 0")
       + prop("Description", "", "101.6 87.63 0")
       + f'\t\t(pin "1"\n\t\t\t(uuid "{U()}")\n\t\t)\n' + instances(vcc_ref) + "\t)\n")

R18_UUID = U()
r18 = (f'\t(symbol\n\t\t(lib_id "Device:R")\n\t\t(at 104.14 121.92 90)\n\t\t(unit 1)\n\t\t(exclude_from_sim no)\n'
       f'\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n\t\t(uuid "{R18_UUID}")\n'
       + prop("Reference", "R18", "104.14 119.38 90", hide=False)
       + prop("Value", "1M", "104.14 124.46 90", hide=False)
       + prop("Footprint", "Resistor_SMD:R_0402_1005Metric", "104.14 121.92 0")
       + prop("Datasheet", "~", "104.14 121.92 0")
       + prop("Description", "TL16C550D oscillator feedback resistor (Rp)", "104.14 121.92 0")
       + prop("LCSC#", "C26083", "104.14 121.92 0")
       + prop("manf#", "0402WGF1004TCE", "104.14 121.92 0")
       + f'\t\t(pin "1"\n\t\t\t(uuid "{U()}")\n\t\t)\n\t\t(pin "2"\n\t\t\t(uuid "{U()}")\n\t\t)\n'
       + instances("R18") + "\t)\n")

new_items = (wire(99.06, 87.63, 101.6, 87.63) + vcc
             + label("XIN", 99.06, 102.87, 0) + label("XOUT", 99.06, 107.95, 0)
             + wire(97.79, 121.92, 100.33, 121.92) + wire(107.95, 121.92, 110.49, 121.92)
             + label("XOUT", 97.79, 121.92, 180) + label("XIN", 110.49, 121.92, 0) + r18)
k = sch.rstrip().rindex(")")
sch = sch[:k] + new_items + sch[k:]
open(sch_path, "w").write(sch)

# ---------------------------------------------------------------- PCB
pcb_path = f"{root}/mega-wifi.kicad_pcb"
pcb = open(pcb_path).read()
for old, new in (('"Net-(U7-XTAL1)"', '"/WiFi/XIN"'), ('"Net-(U7-XTAL2)"', '"/WiFi/XOUT"'),
                 ('"unconnected-(U7-INT-Pad20)"', '"unconnected-(U7-INTRPT-Pad20)"')):
    assert old in pcb, old
    pcb = pcb.replace(old, new)
pcb = sub1(r'\t\(net 125 "unconnected-\(U7-~\{RI\}-Pad27\)"\)\n', "", pcb)


def fix_u7(b):
    b = b.replace('(footprint "Package_DFN_QFN:HVQFN-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm"', f'(footprint "{NEW_FP}"')
    b = sub1(r'\(descr "[^"]*"\)', '(descr "Texas RHB0032E VQFN, 32 Pin (https://www.ti.com/lit/ds/symlink/tl16c550d.pdf)")', b)
    b = sub1(r'\(tags "[^"]*"\)', '(tags "Texas RHB0032E VQFN NoLead")', b)
    b = b.replace('(property "Value" "SC16C550BIBS"', '(property "Value" "TL16C550DRHB"')
    b = b.replace("Package_DFN_QFN:HVQFN-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm", NEW_FP)
    b = b.replace("https://www.nxp.com/docs/en/data-sheet/SC16C550B.pdf", DS)
    b = b.replace('"Parallel to UART"', f'"{DESC}"')
    b = b.replace('(property "LCSC#" "C3310482"', '(property "LCSC#" "C2653239"')
    # paste apertures: 3x3 grid of 0.93 mm squares on 1.15 mm pitch (TI RHB0032E stencil)
    b = re.sub(r"\(at (-?)1\.03 ", r"(at \g<1>1.15 ", b)
    b = re.sub(r"\(at (-?1\.15|0) (-?)1\.03 ", r"(at \1 \g<2>1.15 ", b)
    b = b.replace("(size 0.83 0.83)", "(size 0.93 0.93)")
    b = b.replace("(size 3.1 3.1)", "(size 3.45 3.45)")
    pinfunc = {"6": "SIN", "7": "SOUT", "8": "~{CS2}", "9": "NC", "10": "XIN", "11": "XOUT",
               "12": "~{WR1}", "14": "~{RD1}", "20": "INTRPT", "23": "MR"}

    def pad(m):
        p = m.group(0)
        num = m.group(1)
        if num in pinfunc:
            p = re.sub(r'\(pinfunction "[^"]*"\)', f'(pinfunction "{pinfunc[num]}")', p)
        if num == "9":
            p = p.replace('(pintype "power_in")', '(pintype "passive")')
        if num == "27":
            p = re.sub(r'\(net \d+ "[^"]*"\)', '(net 3 "VCC")', p)
            p = p.replace('(pintype "input+no_connect")', '(pintype "input")')
        return p
    b = re.sub(r'\(pad "(\d+)" smd .*?\(uuid "[^"]+"\)', pad, b, flags=re.S)
    b = b.replace("QFN-32-1EP_5x5mm_P0.5mm_EP3.3x3.3mm.wrl", "QFN-32-1EP_5x5mm_P0.5mm_EP3.45x3.45mm.wrl")
    return b


pcb = edit_block(pcb, '(footprint "Package_DFN_QFN:HVQFN-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm"', fix_u7)


def fix_y1(b):
    b = b.replace('(property "Value" "24 MHz"', '(property "Value" "20 MHz"')
    b = b.replace('(property "LCSC#" "C2901723"', '(property "LCSC#" "C252261"')
    return b


i = pcb.rindex("\n\t(footprint ", 0, pcb.index('(property "Reference" "Y1"')) + 1
pcb = pcb[:i] + fix_y1(pcb[i:block(pcb, i)]) + pcb[block(pcb, i):]

# R18: clone R15 (0402), place across the XIN/XOUT traces under Y1
i = pcb.rindex("\n\t(footprint ", 0, pcb.index('(property "Reference" "R15"')) + 1
r = pcb[i:block(pcb, i)]
r = re.sub(r'\(uuid "[^"]+"\)', lambda m: f'(uuid "{U()}")', r)
r = r.replace("(at 169.418 89.027 90)", "(at 155.2 86.35 0)")
r = re.sub(r"\(at ([^()]*?) 90\)", r"(at \1 0)", r)
r = r.replace('(property "Reference" "R15"\n\t\t\t(at -0.381 -1.143 0)', '(property "Reference" "R18"\n\t\t\t(at -1.55 0 0)')
r = r.replace("(size 1.016 1.016)\n\t\t\t\t\t(thickness 0.1524)", "(size 0.5 0.5)\n\t\t\t\t\t(thickness 0.1)")
r = r.replace('(property "Value" "5k1"', '(property "Value" "1M"')
r = r.replace('(property "Description" "Resistor"', '(property "Description" "TL16C550D oscillator feedback resistor (Rp)"')
r = r.replace('(property "LCSC#" "C25905"', '(property "LCSC#" "C26083"')
r = re.sub(r'\(path "[^"]+"\)', f'(path "/{WIFI_SHEET}/{R18_UUID}")', r)
r = r.replace('(net 2 "GND")', '(net 48 "/WiFi/XOUT")').replace('(net 116 "Net-(P2-CC1)")', '(net 4 "/WiFi/XIN")')
assert '"R18"' in r and "XOUT" in r and "XIN" in r
pcb = pcb[:i] + r + pcb[i:]

# RI stub: pad 27 -> down -> join pad 28 VCC track
seg = lambda x1, y1, x2, y2: (f'\t(segment\n\t\t(start {x1} {y1})\n\t\t(end {x2} {y2})\n\t\t(width 0.2032)\n'
                              f'\t\t(layer "F.Cu")\n\t\t(net 3)\n\t\t(uuid "{U()}")\n\t)\n')
stub = seg(153.414, 92.481, 153.414, 93.368) + seg(153.414, 93.368, 153.914, 93.368)
k = pcb.index("\n\t(segment\n") + 1
pcb = pcb[:k] + stub + pcb[k:]
open(pcb_path, "w").write(pcb)
print("ok")
