#!/usr/bin/env python3
"""Read-only FlashKit MD probe: raw reads at a few addresses, CFI QRY + size, autoselect ID.
usage: fk_probe.py [/dev/cu.usbserial-XXXX]   (needs pyserial)"""
import serial,sys
CMD_ADDR,CMD_LEN,CMD_RD,CMD_WR=0,1,2,3; INC,SINGLE,MODE8=128,64,16
p=serial.Serial(sys.argv[1] if len(sys.argv)>1 else '/dev/cu.usbserial-A10MQJP4',timeout=2)
def addr(a):
    a//=2; return bytes([CMD_ADDR,(a>>16)&255,CMD_ADDR,(a>>8)&255,CMD_ADDR,a&255])
def rd(a,n):
    p.write(addr(a)+bytes([CMD_LEN,(n//2>>8)&255,CMD_LEN,(n//2)&255,CMD_RD|INC])); b=p.read(n)
    assert len(b)==n,f'short read {len(b)}'; return b
def wb(a,v): p.write(addr(a)+bytes([CMD_WR|SINGLE|MODE8,v]))
def ww(a,v): p.write(addr(a)+bytes([CMD_WR|SINGLE,v>>8,v&255]))
h=lambda b:' '.join(f'{x:02x}' for x in b)
ww(0,0xf0)  # make sure flash is in read-array mode
for a in (0x0,0x100,0x1f0,0x200000,0x400000,0x7ffff0):
    print(f'{a:06x}: {h(rd(a,16))}')
# CFI query (same as FlashKitSession.CheckFlash)
wb(0x55*2,0x98); q=rd(0x20,6); cfi=rd(0x20,0x60); ww(0,0xf0)
print('CFI QRY @0x20:',h(q),'->','OK' if q==bytes([0,0x51,0,0x52,0,0x59]) else 'FAIL')
if q==bytes([0,0x51,0,0x52,0,0x59]):
    w=lambda i: cfi[2*(i-0x10)+1]
    print(f'  device size 2^{w(0x27)} bytes')
# Autoselect (AMD/Spansion): expect mfr 0x0001, dev 0x227E
ww(0x555*2,0xaa); ww(0x2aa*2,0x55); ww(0x555*2,0x90)
idb=rd(0,2)+rd(2,2)+rd(0x1c,2)+rd(0x1e,2); ww(0,0xf0)
print('Autoselect mfr/dev/dev2/dev3:',h(idb))
print('after reset   000000:',h(rd(0,16)))
