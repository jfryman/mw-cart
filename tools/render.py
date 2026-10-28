import sys, math
sys.path.insert(0, sys.argv[1]); from sexp import *
pcb, out, X0, Y0, X1, Y1 = sys.argv[2], sys.argv[3], *map(float, sys.argv[4:8])
extra = sys.argv[8] if len(sys.argv) > 8 else ''
b = parse(open(pcb).read()); nets = {n[1]: n[2] for n in find(b, 'net')}
col = lambda n: {'GND': '#2a6', 'VCC': '#c33'}.get(n, '#36c')
s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{X0} {Y0} {X1-X0} {Y1-Y0}" width="{(X1-X0)*80}" height="{(Y1-Y0)*80}"><rect x="{X0}" y="{Y0}" width="{X1-X0}" height="{Y1-Y0}" fill="#111"/>']
for z in find(b, 'zone'):
    if first(z, 'layer') and first(z, 'layer')[1] == 'F.Cu':
        for fp in find(z, 'filled_polygon'):
            pts = ' '.join(f'{p[1]},{p[2]}' for p in first(fp, 'pts')[1:] if p[0] == 'xy')
            s.append(f'<polygon points="{pts}" fill="{col(first(z,"net_name")[1])}" opacity="0.25"/>')
for sg in find(b, 'segment'):
    st, en = first(sg, 'start'), first(sg, 'end'); ly = first(sg, 'layer')[1]
    s.append(f'<line x1="{st[1]}" y1="{st[2]}" x2="{en[1]}" y2="{en[2]}" stroke="{col(nets.get(first(sg,"net")[1]))}" stroke-width="{first(sg,"width")[1]}" stroke-linecap="round" opacity="{1 if ly=="F.Cu" else 0.35}"/>')
for p in pads(b):
    if X0-3 < p['x'] < X1+3 and Y0-3 < p['y'] < Y1+3 and 'F.Cu' in p['layers'] or '*.Cu' in p['layers']:
        w, h = (p['w'], p['h']) if int(p['rot']) % 180 == 0 else (p['h'], p['w'])
        s.append(f'<rect x="{p["x"]-w/2}" y="{p["y"]-h/2}" width="{w}" height="{h}" fill="{col(p["net"])}" stroke="#fff" stroke-width="0.02"/>')
        s.append(f'<text x="{p["x"]}" y="{p["y"]+0.06}" font-size="0.18" fill="#fff" text-anchor="middle">{p["ref"]}.{p["pad"]}</text>')
for v in find(b, 'via'):
    a = first(v, 'at'); s.append(f'<circle cx="{a[1]}" cy="{a[2]}" r="0.355" fill="#aa0"/><circle cx="{a[1]}" cy="{a[2]}" r="0.15" fill="#111"/>')
for x in range(int(X0), int(X1)+1):
    s.append(f'<line x1="{x}" y1="{Y0}" x2="{x}" y2="{Y1}" stroke="#555" stroke-width="0.01"/><text x="{x+0.02}" y="{Y0+0.25}" font-size="0.2" fill="#aaa">{x}</text>')
for y in range(int(Y0), int(Y1)+1):
    s.append(f'<line x1="{X0}" y1="{y}" x2="{X1}" y2="{y}" stroke="#555" stroke-width="0.01"/><text x="{X0+0.02}" y="{y-0.02}" font-size="0.2" fill="#aaa">{y}</text>')
s.append(extra + '</svg>'); open(out, 'w').write('\n'.join(s))
