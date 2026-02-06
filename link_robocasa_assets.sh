#!/usr/bin/env bash
set -euo pipefail

# Build a combined assets dir:
# - robocasa kitchen assets (fixtures/textures/objects/...)
# - robosuite robot meshes (assets/robots/...) required by panda_omron.xml
#
# Everything is symlinked (read-only usage).
LINK="./with-robot-5th/model/robocasa/assets"
LINK_DIR="$(dirname "$LINK")"
ROOT_ABS="$(cd "$(dirname "$0")" && pwd)"
COMBINED_ABS="$ROOT_ABS/robot_module_assets"

[ -d "$ROOT_ABS/robocasa/robocasa/models/assets" ] || { echo "missing: $ROOT_ABS/robocasa/robocasa/models/assets" >&2; exit 1; }
[ -d "$ROOT_ABS/robosuite/robosuite/models/assets/robots" ] || { echo "missing: $ROOT_ABS/robosuite/robosuite/models/assets/robots" >&2; exit 1; }
[ -d "$ROOT_ABS/robosuite/robosuite/models/assets/bases" ] || { echo "missing: $ROOT_ABS/robosuite/robosuite/models/assets/bases" >&2; exit 1; }
[ -d "$ROOT_ABS/robosuite/robosuite/models/assets/grippers" ] || { echo "missing: $ROOT_ABS/robosuite/robosuite/models/assets/grippers" >&2; exit 1; }

[ -d "$COMBINED_ABS" ] || mkdir -p "$COMBINED_ABS"

ln -sfn "$ROOT_ABS/robocasa/robocasa/models/assets/arenas" "$COMBINED_ABS/arenas"
ln -sfn "$ROOT_ABS/robocasa/robocasa/models/assets/fixtures" "$COMBINED_ABS/fixtures"
ln -sfn "$ROOT_ABS/robocasa/robocasa/models/assets/generative_textures" "$COMBINED_ABS/generative_textures"
ln -sfn "$ROOT_ABS/robocasa/robocasa/models/assets/objects" "$COMBINED_ABS/objects"
ln -sfn "$ROOT_ABS/robocasa/robocasa/models/assets/scenes" "$COMBINED_ABS/scenes"
ln -sfn "$ROOT_ABS/robocasa/robocasa/models/assets/textures" "$COMBINED_ABS/textures"
ln -sfn "$ROOT_ABS/robosuite/robosuite/models/assets/bases" "$COMBINED_ABS/bases"
ln -sfn "$ROOT_ABS/robosuite/robosuite/models/assets/grippers" "$COMBINED_ABS/grippers"
ln -sfn "$ROOT_ABS/robosuite/robosuite/models/assets/robots" "$COMBINED_ABS/robots"

[ ! -e "$LINK" ] || [ -L "$LINK" ] || { echo "exists (not symlink): $LINK" >&2; exit 1; }

mkdir -p "$LINK_DIR"
ln -sfn "$COMBINED_ABS" "$LINK"
echo "linked $LINK -> $COMBINED_ABS"
