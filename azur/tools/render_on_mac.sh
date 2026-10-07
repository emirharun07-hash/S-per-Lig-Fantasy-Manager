#!/bin/sh
# Render the AZUR scene on a Mac with an Apple chip (M1 to M5): Cycles on the graphics chip via Metal.
#
#   sh azur/tools/render_on_mac.sh            everything still missing: view plates and passes, then camera moves
#   sh azur/tools/render_on_mac.sh moves      only the camera moves
#   sh azur/tools/render_on_mac.sh queue      only the view plates and passes
#
# First run: installs uv, Python 3.11 and Blender's Python module into azur/.venv (about 1 GB, 5-10 minutes) and
# downloads the CC0 textures (about 300 MB). Finished outputs are skipped; every new output is committed and pushed,
# exactly like the cloud renders. Do not let the cloud render the same job at the same time.
set -e
cd "$(git rev-parse --show-toplevel)"
BRANCH=claude/shopify-notification-signup-o5avym
git fetch -q origin "$BRANCH"
git checkout -q "$BRANCH"
git pull -q --rebase origin "$BRANCH"

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
[ -d azur/.venv ] || uv venv -q -p 3.11 azur/.venv
. azur/.venv/bin/activate
uv pip install -q bpy==5.0.1 numpy pillow scikit-image scipy imageio-ffmpeg

export AZUR_GPU=1
case "${1:-all}" in
  queue) python azur/scene/render_queue.py ;;
  moves) python azur/scene/render_moves.py ;;
  *)     python azur/scene/render_queue.py && python azur/scene/render_moves.py ;;
esac
grep "render device" azur/.cache/queue.log | tail -1
