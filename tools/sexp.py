import re, math, sys
def parse(text):
    tok = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')
    stack=[[]]
    for m in tok.finditer(text):
        t=m.group(0)
        if t=='(': stack.append([])
        elif t==')': x=stack.pop(); stack[-1].append(x)
        else: stack[-1].append(t[1:-1] if t[0]=='"' else t)
    return stack[0][0]
def find(node,key): return [c for c in node if isinstance(c,list) and c and c[0]==key]
def first(node,key):
    r=find(node,key); return r[0] if r else None
def rot(x,y,a):
    a=math.radians(-a); return x*math.cos(a)-y*math.sin(a), x*math.sin(a)+y*math.cos(a)
def pads(board):
    out=[]
    for fp in find(board,'footprint'):
        at=first(fp,'at'); fx,fy=float(at[1]),float(at[2]); fa=float(at[3]) if len(at)>3 else 0
        ref=[p[2] for p in find(fp,'property') if p[1]=='Reference'][0]
        for pd in find(fp,'pad'):
            pa=first(pd,'at'); dx,dy=rot(float(pa[1]),float(pa[2]),fa)
            sz=first(pd,'size'); net=first(pd,'net')
            out.append(dict(ref=ref,pad=pd[1],x=fx+dx,y=fy+dy,w=float(sz[1]),h=float(sz[2]),rot=(float(pa[3]) if len(pa)>3 else 0),net=net[2] if net else '',layers=first(pd,'layers')[1:]))
    return out
