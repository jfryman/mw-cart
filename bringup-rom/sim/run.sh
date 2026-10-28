#!/bin/sh
# Run the bring-up ROM in MAME (headless) against the Lua UART/ESP32 model.
# Usage: sim/run.sh [fault] [snap_seconds]   e.g. sim/run.sh none 6,20
# SIM_CART=path overrides the image (e.g. an 8 MiB one from tools/fk_hiflash.py image).
# Snapshots land in sim/out/snap/genesis/.
set -e
here=$(cd "$(dirname "$0")" && pwd)
out="$here/out"
rm -rf "$out" && mkdir -p "$out"
SIM_FAULT="${1:-none}" SIM_SNAP_AT="${2:-6,20}" \
mame genesis -cart "${SIM_CART:-$here/../mw-revc-bringup.bin}" \
	-noautosave -video none -sound none -nothrottle -skip_gameinfo -state_directory "$out/sta" \
	-snapshot_directory "$out/snap" -cfg_directory "$out/cfg" -nvram_directory "$out/cfg" \
	-autoboot_script "$here/uart_model.lua" 2>&1 | grep -v osd_subst_env || true
ls "$out"/snap/genesis/
