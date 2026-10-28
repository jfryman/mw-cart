# Lode map

- [summary.md](summary.md) — project snapshot: GitHub forks, local workspace layout, board status
- [terminology.md](terminology.md) — domain terms (MegaWiFi, LSD, ACE, Rp, RHB…)
- [practices.md](practices.md) — KiCad 8 format rule, zone-fill transplant, verification gate
- hardware/
  - [summary.md](hardware/summary.md) — block diagram, sheets, key UART nets, board invariants
  - [uart-bridge.md](hardware/uart-bridge.md) — U7 TL16C550DRHB pin map, 20 MHz clock, R18 Rp, RI tie, PCB details
  - [uart-part-selection.md](hardware/uart-part-selection.md) — why TL16C550D, rejected candidates, JLC stock query
- firmware/
  - [uart-baud-coupling.md](firmware/uart-baud-coupling.md) — UART_CLK/UART_BR and LSD_UART_BR across repos; ESP32-C3 fw container build + flashing
  - [bringup-rom.md](firmware/bringup-rom.md) — Rev.C bring-up test ROM, MAME UART model, m68k toolchain traps
- build/
  - [summary.md](build/summary.md) — KiBot CI vs local kicad-cli pipeline, toolchain, JLC CPL contract
  - [kicad-text-editing.md](build/kicad-text-editing.md) — tools/ helpers and s-expr editing patterns
- plans/
  - [rev-c.md](plans/rev-c.md) — Rev.C status, pre-order checks, bench validation plan
  - [github-repos.md](plans/github-repos.md) — GitHub forks, releases, what's in git vs release assets, remotes; how to cut a release
- tmp/ — git-ignored session scraps
