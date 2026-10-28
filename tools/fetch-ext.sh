#!/bin/sh
# Fetch the Espressif KiCad 3D models that mega-wifi.kicad_pcb references through
# ${KICAD8_3RD_PARTY}/3dmodels/com_github_espressif_kicad-libraries/... (ESP32-C3-WROOM-02).
# Creates tools/ext/espressif-kicad (sparse, blobless clone pinned below) and the
# tools/ext/3rdparty tree to point KICAD8_3RD_PARTY at:
#   KICAD8_3RD_PARTY=$PWD/tools/ext/3rdparty python3 -I tools/build_outputs.py . build/rev-c
set -e
REV=dd76561812ab300351234ba6e0ec1295641796f0
ext=$(cd "$(dirname "$0")" && pwd)/ext
mkdir -p "$ext/3rdparty/3dmodels"
if [ ! -d "$ext/espressif-kicad/.git" ]; then
	git clone --filter=blob:none --no-checkout https://github.com/espressif/kicad-libraries.git "$ext/espressif-kicad"
	git -C "$ext/espressif-kicad" sparse-checkout set 3dmodels/espressif.3dshapes
fi
git -C "$ext/espressif-kicad" fetch --quiet origin "$REV" 2>/dev/null || true
git -C "$ext/espressif-kicad" checkout --quiet "$REV"
ln -sfn ../../espressif-kicad/3dmodels "$ext/3rdparty/3dmodels/com_github_espressif_kicad-libraries"
echo "KICAD8_3RD_PARTY=$ext/3rdparty"
