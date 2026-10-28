# Practices

## Source of truth
- KiCad sources in `mw-cart/` are the truth. The top-level `Browse/ Doc/ Fab/` tree
  is the **upstream Rev.B (SC16C550) build**. It is reference only and never edited.
- Work happens on `main` of `jfryman/mw-cart` (public). Commit or push only when the user asks.
  Generated outputs (`build/`, KiBot trees, `*.bin`) never go in git; they ship as release assets
  built from the tagged commit ([plans/github-repos.md](plans/github-repos.md)).
- Before pushing, scan the files you're adding for personal paths, hostnames and secrets: the repos are public.

## Platforms: Linux and macOS, never Windows
The user works on either **Omarchy (Arch Linux)** or **macOS (Apple silicon)**, and older notes come
from a Fedora/Asahi box. Everything in the repo must run on both:
- Find tools by lookup order, never by hard-coded path: env override → PATH → KiCad.app →
  flatpak (`tools/kc`, `tools/kipy`, `build_outputs.py`).
- Cross toolchains run in containers that work with **Podman or Docker**
  (`bringup-rom/container.sh`, the ESP-IDF image). Don't depend on a distro package that only one OS has.
- Scripts are POSIX `sh` or Python 3. Avoid GNU-only and BSD-only flags (`sed -i`, `truncate`,
  `readlink -f`) outside containers.
- Serial ports: FlashKit is `/dev/cu.usbserial-*` (macOS) or `/dev/ttyUSB*` (Linux); the cart's ESP32 is
  `/dev/cu.usbmodem*` or `/dev/ttyACM*`. Linux needs the user in `uucp` (Arch) or `dialout`.
- zsh (macOS default) doesn't word-split unquoted `$var`; write scripts for `sh`.

## Keep sources in KiCad 8 format
Upstream CI uses `ghcr.io/inti-cmnb/kicad8_auto`. Local machines have KiCad 10 (KiCad.app,
pacman or flatpak). Opening and saving in the KiCad 10 GUI or `pcbnew.SaveBoard` would upgrade the
file format and break the upstream CI. So:
- Edit `.kicad_sch`/`.kicad_pcb` **as text** (Python, s-expr aware), never via a KiCad 10 save.
- Use KiCad 10 only for read-only work: `kicad-cli` ERC/DRC/exports, and zone filling
  into a *scratch copy*.
- Check the header after edits: `(version 20240108)` / `(generator_version "8.0")`.

```bash
head -4 mw-cart/mega-wifi.kicad_pcb   # must still say version 20240108
```

## Zone fills
Fills are stored in the PCB file and KiBot does **not** refill them. After any copper
change, refill and transplant (see [build/kicad-text-editing.md](build/kicad-text-editing.md)):

```bash
tools/kipy tools/fill.py $PWD/mega-wifi.kicad_pcb /tmp/filled.kicad_pcb   # repo root
python3 -I tools/transplant.py mega-wifi.kicad_pcb /tmp/filled.kicad_pcb
```

## Verification gate (run after every hardware edit)
1. `tools/kc sch erc --severity-all mega-wifi.kicad_sch`. The expected baseline is only
   `footprint_link_issues` (no lib table on this machine) and 28 `pin_to_pin` notes
   (power-output and tri-state pairs, inherited from upstream).
   Once any `kc pcb render` has run, KiCad 10 creates a library table, and DRC then also
   lists about 47 `lib_footprint_mismatch` items (board footprints are the KiCad 8 versions).
   That's environmental, so ignore it.
2. `tools/kc pcb drc --schematic-parity --severity-all mega-wifi.kicad_pcb`. The result
   must show 0 unconnected items and 0 parity issues. The accepted remainder is 3
   missing_courtyard, 3 silk_edge_clearance, 2 silk_over_copper (Y1 silk over R18 pads)
   and 1 courtyards_overlap (R18↔Y1).
3. Diff the result against a baseline run on `master` (use a `git worktree` in scratch).

## Parts
- Prefer parts JLCPCB stocks, and check stock live through the JLC search API (see
  [hardware/uart-part-selection.md](hardware/uart-part-selection.md)).
- Every BOM line carries both `LCSC#` and `manf#`. DRC parity flags footprints missing
  fields that the symbol has.
