#!/bin/sh
# Run a command for the bring-up ROM inside the Fedora toolchain container.
#   ./container.sh make
#   ./container.sh sim/run.sh none 16
#   SIM_CART=hi.bin SIM_HI=hi.bin ./container.sh sim/run.sh none 16   (paths relative to bringup-rom/)
# Uses podman if present, else docker. Builds the image on first use.
set -e
here=$(cd "$(dirname "$0")" && pwd)
img=mw-bringup-rom:fedora42
if command -v podman >/dev/null 2>&1; then rt=podman; vol=":Z"; user="--userns=keep-id"
elif command -v docker >/dev/null 2>&1; then rt=docker; vol=""; user="--user $(id -u):$(id -g)"
else echo "container.sh: need podman or docker" >&2; exit 127; fi
$rt image inspect $img >/dev/null 2>&1 || $rt build -t $img -f "$here/Containerfile" "$here"
envs=""
for v in SIM_CART SIM_HI SIM_FAULT SIM_SNAP_AT; do
	eval "val=\${$v:-}"; [ -n "$val" ] && envs="$envs -e $v=$val"
done
# shellcheck disable=SC2086
exec $rt run --rm $user -v "$here":/w$vol -w /w -e HOME=/tmp -e XDG_RUNTIME_DIR=/tmp \
	-e SDL_VIDEODRIVER=dummy -e SDL_AUDIODRIVER=dummy $envs $img "$@"
