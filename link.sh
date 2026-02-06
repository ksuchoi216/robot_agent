#!/usr/bin/env bash
set -euo pipefail

LINK="./with-robot-5th/model/robocasa/assets"
LINK_DIR="$(dirname "$LINK")"
TARGET_ABS="$(cd "$(dirname "$0")" && pwd)/data/assets"

[ -d "$TARGET_ABS" ] || { echo "missing: $TARGET_ABS" >&2; exit 1; }
[ ! -e "$LINK" ] || [ -L "$LINK" ] || { echo "exists (not symlink): $LINK" >&2; exit 1; }

ln -sfn "$TARGET_ABS" "$LINK"
echo "linked $LINK -> $TARGET_ABS"
