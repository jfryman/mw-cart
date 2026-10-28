# MegaWiFi Rev.C bring-up ROM

A standalone Mega Drive ROM (no SGDK) that checks a freshly assembled Rev.C
cart: the TL16C550D UART (U7), the 20 MHz crystal, and the 1.25 Mbaud link to
the ESP32-C3. Image: `mw-revc-bringup.bin` (128 KiB). Program it into the cart's
S29GL064N flash at address 0.

## Tests (run top to bottom, results on screen)

| # | Test | Proves | Typical failure meaning |
|---|------|--------|-------------------------|
| 1 | SPR scratch | 68k ↔ U7 data bus D0–D7, ~CS (~TIME), ~RD/~WR | U7 not soldered, a data line open/short, CS not reaching U7 |
| 2 | reg decode | A0–A2 decode, DLAB, DLL/DLM vs RHR/IER aliasing | address line open/short (shows which register and W/R values) |
| 3 | LSR idle | FIFO reset, transmitter idle (`LSR=60`) | U7 held in reset (MR / Q1 / R9), no clock |
| 4 | loopback 8K | 8 KiB through U7's internal loop at divisor 1 (1.25 Mbaud) | oscillator not running (TX stuck), RX FIFO / read-strobe trouble |
| 5 | modem loop | MCR→MSR internal paths | U7 internal fault (rare) |
| 6 | crystal | Measures the UART clock against the VDP frame rate. Expect **20.0 MHz** (±1.5 %) | 24.00 = wrong crystal fitted; 0 / TX stuck = no oscillation (check R18, C12/C13) |
| 9 | flash A17-A22 | Pattern blocks written by `tools/fk_hiflash.py`. Low half (`$020000`–`$3E0000`): A17–A21 reach the flash. High half (`$400000`–`$7E0000`): the flat-8 MiB hack (R1, `~CART_IN` = A22). Then 300 frames of reads alternating below/above 4 MiB, so `~CART_IN` flips on every access | `SKIP no pattern`: run the script. `@X reads Y An`: address line n open/short (A22 = R1 / `~CART_IN` path). `blank: R2? no 8MiB map`: the console never maps the cart above 4 MiB. `toggle … err N`: errors while `~CART_IN` toggles |
| 7 | ESP32 version | Resets the ESP32 via ~DTR (with ~RTS/GPIO9 held high), then LSD `MW_CMD_VERSION` | "no reply": ESP firmware not built with `LSD_UART_BR 1250000`, or TX/RX/CTS wiring |
| 8 | echo stress | `MW_CMD_ECHO`, 1–1024 byte payloads, forever, under auto RTS/CTS | any error count > 0: data loss. See below |

Test 9 runs after test 6 and before 7, because 8 never ends. It does not affect the
"UART + crystal OK" line. Press **START** to rerun everything.

### Reading the echo stress test
This test is the field check for the one open timing risk in Rev.C. The TL16C550D
needs ~CS to stay asserted 10 ns after ~RD/~WR rises (the NXP part needed 0 ns).
If ~TIME drops too early, RHR reads may not pop the RX FIFO, or THR writes may
be lost. That shows up here as `mismatch` (duplicated or dropped bytes) or
`framing` errors. Leave it running for several minutes. **0 errors over
10,000+ frames** is the pass bar. Errors that appear only at the larger sizes
point at flow control (`LSR err` with OE set = RX overrun).

The firmware on the ESP32 must be MegaWiFi `mw-fw-rtos` with `LSD_UART_BR 1250000`
(`main/lsd.h`), flashed over the USB-C port.

## Flashing (FlashKit MD)

Use [flashkit-md](https://github.com/jfryman/flashkit-md-dotnet) **v1.10.5 or later**. Older
versions also probe `/dev/cu.usbmodem*` / `ttyACM*`, and grab the cart's ESP32 if its USB-C is plugged in.

```sh
flashkit-md info
flashkit-md read-rom --trust-header cart-backup.bin   # write-rom erases the flash
flashkit-md write-rom mw-revc-bringup.bin             # no --full-erase on old (<1.11) versions
```

| | macOS | Linux |
|---|---|---|
| FlashKit MD (FTDI) | `/dev/cu.usbserial-*` | `/dev/ttyUSB*` |
| cart USB-C (ESP32) | `/dev/cu.usbmodem*` | `/dev/ttyACM*` |
| permissions | none needed | user in `uucp` (Arch/Omarchy) or `dialout` (Fedora/Debian) |

`tools/fk_probe.py` gives a read-only check of a new cart: raw reads, CFI and the flash ID.
It needs pyserial (`pip install pyserial`) and finds the FlashKit on either OS.

### Running it on a Rev.B cart (NXP UART, 24 MHz, stock firmware)
Tests 1–5 PASS. Test 6 FAILs at ~24.00 MHz (expected). Tests 7–8 PASS, because divisor 1
at 24 MHz is 1.5 Mbaud, the stock firmware's rate. A failure in 7–8 on Rev.B means a ROM bug.

### Test 9: writing the pattern

```sh
python3 tools/fk_hiflash.py write    # needs pyserial; auto-finds /dev/cu.usbserial*
python3 tools/fk_hiflash.py verify   # read-only check of all 13 blocks
python3 tools/fk_hiflash.py erase    # back to blank
```

The script checks CFI and an 8 MiB chip first. It only erases the 64 KiB blocks holding
pattern blocks, never `$000000`–`$01FFFF`. It refuses to erase a block holding anything but
0xFF or its own pattern unless you pass `--force`. Write the bring-up ROM first:
`write-rom` erases only what the ROM covers, so the pattern survives later ROM rewrites.
`fk_hiflash.py image ROM.bin OUT.bin` builds the same 8 MiB image offline for emulators.

With a Mega-CD attached and R1 fitted, test 9 is also the check for the
"cart answers in the CD's region" behaviour (see `lode/hardware/summary.md`).

## Build

Works the same on Linux and macOS through a container (Podman or Docker). `container.sh` builds
the image from `Containerfile` (Fedora 42: `gcc-m68k-linux-gnu`, MAME) on first use:

```sh
./container.sh make clean && ./container.sh make      # always clean for a release image
```

On Fedora you can also build natively: `sudo dnf install gcc-m68k-linux-gnu binutils-m68k-linux-gnu`,
then `make`. Other distros' m68k cross compilers are untested; use the container.

`make` also runs `check`, which rejects any 68020+ instruction in the image.

**Toolchain notes (each of these produced a real crash during development):**
- The distro `libgcc` for m68k is built for 68020+ (its `__umodsi3` uses `bsr.l`),
  so it is **not linked**. `lib68k.c` provides 68000-safe `__mulsi3`/`__udivsi3`/...
- The Linux-targeted gcc defaults to `-mno-strict-align`, and merged byte stores into
  odd addresses (an address error on a 68000). The Makefile passes `-mstrict-align`.
- 64-bit arithmetic is avoided entirely (libgcc's 64-bit divide is 68020-only).

## Simulation (MAME + Lua UART model)

`sim/uart_model.lua` is a behavioural model of the TL16C550D at 20 MHz (FIFOs,
loopback, divisor-accurate byte timing, LSR/MSR, auto-RTS) plus a fake ESP32
that answers VERSION and ECHO. MAME runs the ROM headless against it:

```sh
./container.sh sim/run.sh none 6,20   # or natively on Fedora (dnf install mame): sim/run.sh ...
sim/run.sh none 6,20      # all tests pass; snapshots in sim/out/snap/genesis/
sim/run.sh noesp 8        # test 7 must FAIL with the firmware hint
sim/run.sh corrupt 12     # test 8 must count mismatches
# test 9: SIM_CART = 8 MiB image from fk_hiflash.py image; SIM_HI = image served at
# $400000+ (models the R1 hack; MAME maps a plain cart below 4 MiB only)
python3 tools/fk_hiflash.py image mw-revc-bringup.bin sim/hi.bin
SIM_CART=sim/hi.bin SIM_HI=sim/hi.bin ./container.sh sim/run.sh none 16   # paths relative to bringup-rom/
SIM_CART=hi.bin SIM_HI=hi.bin sim/run.sh none 16   # test 9 PASS L6 H7
SIM_CART=hi.bin sim/run.sh none 16                 # test 9 FAIL "R2? no 8MiB map"
```
MAME repeats a 128 KiB image across the cart space, so the plain ROM shows test 9 SKIP
only because nothing carries the `MWAT` marker, not because the reads are blank.

Fedora's `/etc/mame/mame.ini` sets `autosave 1`. `run.sh` passes `-noautosave`;
without it MAME silently restores the last machine state and every run lies.

The sim checks the ROM's logic, not the hardware. Real timing (CS hold, the 68k
bus) only shows up on a real board.

## Files
- `boot.s`: vectors, header, C start-up, VINT frame counter, per-vector fault stubs
  (vector at `$FFFF00`, SP at `$FFFF02`, backdrop turns red)
- `main.c`: tests; `tools/fk_hiflash.py`: test-9 pattern writer (FlashKit MD); `uart.h`: U7 register map; `vdp.c`: text console; `lib68k.c`: arithmetic helpers
- `font.c`/`font.h`: 8×8 font from doragasu's mw-api (MPL 2.0)
