# Plan: Rev.C — replace SC16C550BIBS with TL16C550DRHB

Branch: `mw-cart` → `rev-c` (from upstream `master` 8ff38d9). Committed as
`0f4f06a` ("Rev.C: replace SC16C550BIBS with TI TL16C550DRHB"), published on `jfryman/mw-cart` `main`. Board label: **Rev.C** (credits
doragasu 2024, jfryman 2026). Target: 10 assembled boards from JLCPCB.

```mermaid
flowchart LR
  A[Pick part ✅] --> B[Schematic ✅] --> C[PCB ✅] --> D[ERC/DRC ✅] --> E[Rev.C label + assets ✅]
  E --> F[Paper validation ✅] --> R[Bring-up ROM ✅ sim] --> G[JLC DFM/BOM review ✅] --> H[Order 10 — in production, U7 shortage ⏳]
  H --> I[ESP fw 1.25M ✅] --> J[Bench validation: board 1 ✅, boards 2–10 ⏳]
```

## Done (current state)
- U7 is a TL16C550DRHB with the RHB0032E footprint, and RI is tied to VCC.
  See [../hardware/uart-bridge.md](../hardware/uart-bridge.md).
- Y1 is 20 MHz (C252261). R18 is a new 1 MΩ Rp (C26083).
- ERC/DRC are at baseline plus the accepted R18↔Y1 courtyard overlap. Schematic parity: 0 issues.
- Rev.C title blocks and silkscreen are in place (front credit line at 0.8×0.7 mm text to clear the OSHW logo).
- Order files are in `build/rev-c/`. Upload **only** these (paths from the workspace root):
  - `build/rev-c/Fab/Manufacturers/mega-wifi-JLCPCB.zip`
  - `build/rev-c/Fab/Manufacturers/JLCPCB/mega-wifi_bom_jlc.csv` (U7 = TL16C550DRHB, C2653239)
  - `build/rev-c/Fab/Manufacturers/JLCPCB/mega-wifi_cpl_jlc.csv`
  - Trap: the top-level `Fab/Manufacturers/` holds the **Rev.B** files, with the same filenames.
    Their BOM lists SC16C550BIBS (C3310482), and JLC rejects it as out of stock.
- Paper validation:
  - Pinout checked against TI's package drawing.
  - Bus timing compared with the NXP part; the only open item is the 10 ns CS hold.
  - BlastEm was ruled out as a hardware check.

## Order status (JLCPCB, 10 assembled boards)
- Order placed with the `build/rev-c/` files (U7 = C2653239 TL16C550DRHBR).
- **Open: U7 short by 1 on one board.** On 2026-10-21 JLC reported that one C2653239
  was missing or defective in production. JLC had no stock of it, either in the user's
  private library or in its public one. Requested fix: substitute **C1523590**
  (TL16C550DRHB). It is the same TI die, VQFN-32 RHB package, pinout and CPL rotation,
  shipped in a tube instead of tape & reel. JLC public stock was 3 that day. Fallback: leave U7
  unpopulated on that board and hand-solder it later. The user is waiting for JLC's answer.
  - If that board ships without U7: it still boots ROMs from flash, but it has no ESP32
    link. Fitting U7 means 0.5 mm-pitch QFN with EP rework (hot air or hotplate).
    Spares are scarce: market stock of TL16C550DRHB(R) was 0 + 3 on 2026-10-21.
  - Bench note: on that board, check that U7's pin-1 orientation matches the others.
- [ ] Record JLC's answer here (substituted / left unpopulated).
- [x] Published as a public fork with release assets ([github-repos.md](github-repos.md)). The full KiBot
      output (Browse HTML, iBoM, other fab houses) is still not generated.
- [ ] Optional: run the bring-up ROM on an existing Rev.B cart (via FlashKit MD) to prove the
      ROM on real hardware before Rev.C boards arrive.

## After boards arrive (bench validation)
Boards arrived 2026-10-27. First board on USB-C only:
- [x] 3.3 V rail up from VBUS (D2 → U2). U8 enumerates as `303a:1001` "USB JTAG_serial debug unit"
      (macOS `/dev/cu.usbmodem101`, MAC 68:c6:3a:3a:e6:1c, ESP32-C3 rev v0.4, 4 MB flash 0x46/0x4016).
- U8 ships **blank**: ROM loops on `invalid header: 0xffffffff`, the watchdog resets it every ~2.6 s,
  and USB drops and re-enumerates each cycle.
- [x] Board 1: `mw-fw-rtos-merged.bin` (1.25 Mbaud) flashed over USB-C and hash-verified. It boots from
      flash (`SPI_FAST_FLASH_BOOT`) and stays on USB; the app logs on UART0 (to U7), so USB stays quiet.
- [x] Board 1 on FlashKit MD (cart edge only, USB-C unplugged): FlashKit enumerates as FTDI FT245R
      `0403:6001` (`/dev/cu.usbserial-A10MQJP4`). CFI `QRY` OK, size 2^23 (8 MiB), autoselect ID
      `0001 / 227E 2210 2200` (Spansion S29GL064N family). Blank flash reads `0xFF` everywhere, which is
      why `flashkit-md info` shows "Unknown / 0K". The read-only probe is `bringup-rom/tools/fk_probe.py`.
      FlashKit client: use `flashkit-md-dotnet` **≥ v1.10.5**. Older builds auto-probed every
      `/dev/cu.usbmodem*`, so a cart with USB-C plugged in had its ESP32 grabbed as if it were the
      programmer (and reset). v1.10.5 auto-detects only FTDI `cu.usbserial*`, so cart USB-C and the
      FlashKit can be connected at the same time. Also, `flashkit-md write-rom` caps images at 4 MB; the cart has 8 MiB.
- [x] Board 1: `mw-revc-bringup.bin` written with `flashkit-md write-rom`, then read back independently:
      CRC32 `8D8BE3F4`, 0 mismatches over 128 KB (covers D0–D15 and A1–A16; A17–A22 not exercised yet).
- [x] Board 1 in a Mega Drive (2026-10-28): **tests 1–8 all pass**. Test 8 echo stress ran ≥1k frames
      at 16 KB with 0 errors (user report), also on the full Tower of Power (Mega-CD + 32X in the bus
      path, which adds delay: extra margin on the CS-hold risk). The 68k ↔ U7 ↔ ESP32 path at 1.25 Mbaud works.
- [ ] Power-up: 3.3 V rail, U7 not hot. Scope Y1 for 20 MHz at XOUT with a ×10 probe
      (Rp = R18 should make it start every time).
- [ ] (board 1 flashed, see above) Flash `bringup-rom/mw-revc-bringup.bin` on each board (built and sim-verified, see
      [../firmware/bringup-rom.md](../firmware/bringup-rom.md)). Tests 1–6 need no ESP firmware.
      Tests 7–8 need mw-fw-rtos with `LSD_UART_BR 1250000`.
- [x] Board 1 (2026-10-28): bring-up ROM with test 9 (CRC32 `EC8415F0`) written, plus all 13 `fk_hiflash.py`
      pattern blocks (read back OK, ROM region unchanged). From the FlashKit side, the cart's flash
      stores and returns data above 4 MiB.
- [ ] Second board (2026-10-28): bring-up ROM `EC8415F0` + test 9 pattern written and read back OK.
      ESP32 still blank, so tests 7–8 fail ("no reply"); flash mw-fw-rtos over USB-C next.
- [x] Board 1 on the Tower of Power (Mega-CD + 32X attached), 2026-10-28: **tests 1–9 all pass**. Test 9
      read L6 H7 and passed its ~5 s `~CART_IN` toggle phase, so the flat-8 MiB map works on real
      hardware with a Mega-CD attached. Test 8 is looping for a long soak.
- [ ] Timing: soak test 8 (echo stress) to 10k+ frames with 0 errors (board 1: ≥1k clean so far).
      Optionally use a logic analyser on ~TIME vs ~OE / ~W at U7 (TI needs 10 ns CS hold).
- [ ] Firmware (board 1 done): mw-fw-rtos `LSD_UART_BR 1250000` flashed over USB-C on each board. See
      [../firmware/uart-baud-coupling.md](../firmware/uart-baud-coupling.md).

## Decisions
- 2026-10-06: stay at 20 MHz / 1.25 Mbaud (in spec). Considered and rejected:
  - Overclocking the TL16C550D to 24 MHz: it would keep 1.5 Mbaud and existing ROMs
    working, but it is 20% over TI's 3.3 V rating.
  - TL16C752D / SC16C752B / XR16L580 (TQFP-48): in spec at 1.5–3 Mbaud, but they need a
    re-layout and EFR-based flow control, so existing ROMs would break anyway.

## Risks
- CS-hold timing (above): no errors in ≥1k echo-stress frames on board 1, so it's working in practice;
  margin is still unmeasured (no logic-analyser capture yet).
- JLC may flag U7's rotation in DFM if its TL16C550 3D model's pin 1 differs from the NXP
  one. The CPL keeps 180° (same land pattern and pin 1 location).
- 0–70 °C commercial grade is fine for a console cart.
- U7 supply is exhausted. Any future Rev.C run will need the TL16C550DRHB(R) restocked,
  or a pre-buy through Global Sourcing / DigiKey / Mouser before ordering.
- Full KiBot output (Browse HTML, iBoM, xlsx BOMs, other fab houses) isn't generated
  locally; see [../build/summary.md](../build/summary.md). It isn't needed for a JLC order.
