"""Copy filled_polygon blocks from a KiCad-10-saved board into the KiCad-8 source, matched by zone uuid."""
import re, sys
src, filled = open(sys.argv[1]).read(), open(sys.argv[2]).read()
def blocks(text, head):
    out = []
    for m in re.finditer(r'\n(\t+)\(' + head + r'\b', text):
        i = m.start() + 1; d = 0; j = i; q = False
        while True:
            c = text[j]
            if q:
                if c == '\\': j += 1
                elif c == '"': q = False
            elif c == '"': q = True
            elif c == '(': d += 1
            elif c == ')':
                d -= 1
                if d == 0: break
            j += 1
        out.append((i, j + 1))
    return out
fz = {}
for i, j in blocks(filled, 'zone'):
    z = filled[i:j]; u = re.search(r'\(uuid "([^"]+)"\)', z).group(1)
    fz[u] = [z[a:b] for a, b in blocks(z, 'filled_polygon')]
res, last, n = [], 0, 0
for i, j in blocks(src, 'zone'):
    z = src[i:j]; u = re.search(r'\(uuid "([^"]+)"\)', z).group(1)
    fps = blocks(z, 'filled_polygon')
    assert u in fz, u
    if fps:
        a, b = fps[0][0], fps[-1][1]
        indent = z[z.rindex('\n', 0, a) + 1:a]
        newz = z[:a] + ('\n' + indent).join(fz[u]) + z[b:]
    else:
        assert not fz[u], f"zone {u} had no fill but now does"
        newz = z
    res.append(src[last:i]); res.append(newz); last = j; n += 1
res.append(src[last:]); open(sys.argv[1], 'w').write(''.join(res)); print('zones', n)
