#!/usr/bin/env python3
"""Write / verify / erase the test-9 address-pattern blocks on a MegaWiFi cart
through a FlashKit MD (FTDI FT245R, cart edge).

Test 9 in the bring-up ROM reads these blocks back from the 68000 side:
  - low half ($020000-$3E0000): proves A17-A21 reach the flash (any cart)
  - high half ($400000-$7E0000): proves the flat-8MiB hack (R1: ~CART_IN = A22)

Each block is 256 bytes and carries its own address, so an aliased read names
the broken address line. The block layout MUST match hb_* in ../main.c.

Safety: needs a CFI flash that reports 8 MiB; only erases the 64 KiB blocks that
hold a pattern block; refuses to erase a block holding anything but 0xFF or our
own pattern (use --force only if you know the cart holds nothing you want).
The bring-up ROM itself ($000000-$01FFFF) is never touched.

usage: fk_hiflash.py [--port /dev/cu.usbserial-XXXX] [--force] {write,verify,erase}
       fk_hiflash.py image ROM.bin OUT.bin   (offline: 8 MiB image = ROM + blocks, for emulators)
write/verify/erase need pyserial.  Protocol mirrors flashkit-md-dotnet src/FlashKit.Core/Device.cs.
"""
import argparse
import glob
import sys

BLOCKS = [0x020000, 0x040000, 0x080000, 0x100000, 0x200000, 0x3E0000,   # A17..A21
          0x400000, 0x420000, 0x440000, 0x480000, 0x500000, 0x600000, 0x7E0000]  # A22 + hack
BLOCK_WORDS = 128
ERASE_BYTES = 0x10000            # one FlashKit erase = 64 KiB (8 sector cmds, 8 KiB stride)
CHIP_BYTES = 8 * 1024 * 1024

CMD_ADDR, CMD_LEN, CMD_RD, CMD_WR, CMD_RY, CMD_DELAY = 0, 1, 2, 3, 4, 5
PAR_INC, PAR_SINGLE, PAR_MODE8 = 128, 64, 16


def pattern(addr):
    """Big-endian bytes of the block at addr, exactly as the 68000 reads them."""
    words = [0x4D57, 0x4154,                       # "MWAT"
             addr >> 16, addr & 0xFFFF,
             ~(addr >> 16) & 0xFFFF, ~addr & 0xFFFF]
    s = (0xACE1 ^ (addr >> 8)) & 0xFFFF or 1
    while len(words) < BLOCK_WORDS:
        s = (s >> 1) ^ (0xB400 if s & 1 else 0)
        words.append(s)
    return b''.join(w.to_bytes(2, 'big') for w in words)


class FlashKit:
    def __init__(self, port):
        import serial
        self.p = serial.Serial(port, timeout=5)

    def _addr(self, a):
        a //= 2
        return bytes([CMD_ADDR, (a >> 16) & 255, CMD_ADDR, (a >> 8) & 255, CMD_ADDR, a & 255])

    def delay(self, v):
        self.p.write(bytes([CMD_DELAY, v]))

    def read(self, a, n):
        out = b''
        self.p.write(self._addr(a))
        while n:
            k = min(n, 0x10000)
            self.p.write(bytes([CMD_LEN, (k // 2 >> 8) & 255, CMD_LEN, (k // 2) & 255, CMD_RD | PAR_INC]))
            b = self.p.read(k)
            if len(b) != k:
                sys.exit(f'FlashKit: short read ({len(b)}/{k} bytes) at {a:06X}')
            out += b
            n -= k
        return out

    def wbyte(self, a, v):
        self.p.write(self._addr(a) + bytes([CMD_WR | PAR_SINGLE | PAR_MODE8, v]))

    def wword(self, a, v):
        self.p.write(self._addr(a) + bytes([CMD_WR | PAR_SINGLE, v >> 8, v & 255]))

    def ry(self):
        """Wait for the flash RY/BY line, then a dummy read to sync with the FlashKit."""
        self.p.write(bytes([CMD_RY, CMD_RD | PAR_SINGLE]))
        if len(self.p.read(2)) != 2:
            sys.exit('FlashKit: timeout waiting for flash ready')

    def reset_bypass(self):        # Device.flashResetByPass
        self.wword(0, 0xF0)
        self.wbyte(0, 0x90)
        self.wbyte(0, 0x00)

    def cfi(self):
        self.wbyte(0x55 * 2, 0x98)
        q = self.read(0x20, 0x60)
        self.wword(0, 0xF0)
        ok = q[:6] == bytes([0, 0x51, 0, 0x52, 0, 0x59])
        size = 1 << q[2 * (0x27 - 0x10) + 1] if ok else 0
        return ok, size

    def erase64k(self, a):        # Device.flashErase
        self.wword(0x555 * 2, 0xAA)
        self.wword(0x2AA * 2, 0x55)
        self.wword(0x555 * 2, 0x80)
        self.wword(0x555 * 2, 0xAA)
        self.wword(0x2AA * 2, 0x55)
        cmd = b''.join(self._addr(a + i * 0x2000) + bytes([CMD_WR | PAR_SINGLE | PAR_MODE8, 0x30])
                       for i in range(8))
        self.p.write(cmd)
        self.ry()

    def program(self, a, data):   # unlock bypass + Device.flashWrite
        self.wbyte(0x555 * 2, 0xAA)
        self.wbyte(0x2AA * 2, 0x55)
        self.wbyte(0x555 * 2, 0x20)
        self.p.write(self._addr(a))
        cmd = b''.join(bytes([CMD_WR | PAR_SINGLE | PAR_MODE8, 0xA0,
                              CMD_WR | PAR_SINGLE | PAR_INC, data[i], data[i + 1], CMD_RY])
                       for i in range(0, len(data), 2))
        self.p.write(cmd)
        self.reset_bypass()
        self.ry()


def find_port():
    ports = sorted(glob.glob('/dev/cu.usbserial*') + glob.glob('/dev/ttyUSB*'))
    if not ports:
        sys.exit('no FlashKit found (expected /dev/cu.usbserial* or /dev/ttyUSB*); use --port')
    return ports[0]


def classify(fk, a):
    """'ok', 'blank' or 'other' for the 64 KiB erase block starting at a."""
    blk = fk.read(a, ERASE_BYTES)
    rest_blank = blk[2 * BLOCK_WORDS:] == b'\xff' * (ERASE_BYTES - 2 * BLOCK_WORDS)
    head = blk[:2 * BLOCK_WORDS]
    if rest_blank and head == pattern(a):
        return 'ok'
    if rest_blank and head == b'\xff' * len(head):
        return 'blank'
    return 'other'


def main():
    ap = argparse.ArgumentParser(description='Write/verify/erase the test-9 flash pattern blocks.')
    ap.add_argument('cmd', nargs='?', default='write', choices=['write', 'verify', 'erase', 'image'])
    ap.add_argument('files', nargs='*', help='image: ROM.bin OUT.bin')
    ap.add_argument('--port')
    ap.add_argument('--force', action='store_true',
                    help='erase pattern blocks even if they hold other data')
    args = ap.parse_args()

    if args.cmd == 'image':
        if len(args.files) != 2:
            ap.error('image needs ROM.bin OUT.bin')
        rom = open(args.files[0], 'rb').read()
        if len(rom) > BLOCKS[0]:
            sys.exit(f'ROM is {len(rom)} bytes; it would overlap the block at {BLOCKS[0]:06X}')
        img = bytearray(rom + b'\xff' * (CHIP_BYTES - len(rom)))
        for a in BLOCKS:
            img[a:a + 2 * BLOCK_WORDS] = pattern(a)
        open(args.files[1], 'wb').write(img)
        print(f'wrote {args.files[1]}: 8 MiB, ROM + {len(BLOCKS)} pattern blocks')
        return 0

    fk = FlashKit(args.port or find_port())
    fk.delay(1)
    fk.wword(0, 0xF0)
    ok, size = fk.cfi()
    if not ok:
        sys.exit('no CFI flash answered on the cart bus (cart seated? FlashKit powered?)')
    if size != CHIP_BYTES:
        sys.exit(f'flash reports {size // 1024} KiB, expected 8 MiB (S29GL064N); refusing')
    print(f'CFI OK, 8 MiB flash on {fk.p.port}')

    state = {a: classify(fk, a) for a in BLOCKS}
    others = [a for a in BLOCKS if state[a] == 'other']

    if args.cmd == 'verify':
        for a in BLOCKS:
            print(f'  {a:06X}: {state[a]}')
        bad = [a for a in BLOCKS if state[a] != 'ok']
        print('verify:', 'all 13 blocks OK' if not bad else f'{len(bad)} block(s) not OK')
        return 1 if bad else 0

    if others and not args.force:
        for a in others:
            print(f'  {a:06X}: 64 KiB block holds data that is not ours')
        sys.exit('refusing to erase; re-run with --force if the cart holds nothing you need')

    todo = [a for a in BLOCKS if state[a] != ('blank' if args.cmd == 'erase' else 'ok')]
    fk.delay(0)
    for a in todo:
        if state[a] != 'blank':
            fk.erase64k(a)
        if args.cmd == 'write':
            fk.program(a, pattern(a))
        print(f'  {a:06X}: {"erased" if args.cmd == "erase" else "written"}')
    fk.delay(1)
    fk.wword(0, 0xF0)

    want = 'blank' if args.cmd == 'erase' else 'ok'
    bad = [a for a in BLOCKS if classify(fk, a) != want]
    if bad:
        sys.exit('read-back FAILED at ' + ', '.join(f'{a:06X}' for a in bad))
    print(f'{args.cmd}: {len(todo)} block(s) changed, all 13 read back {want}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
