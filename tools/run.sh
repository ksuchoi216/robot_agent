#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROBOT_DIR="${ROOT_DIR}/with-robot-4th-lab/robot"

ENV_NAME="${CONDA_ENV:-robot}"
MJ_PYTHON="${MJ_PYTHON:-mjpython}"

TARGET="${1:-camera}"
if [[ "${TARGET}" == "main" ]]; then
  ENTRYPOINT="main.py"
  shift
elif [[ "${TARGET}" == "camera" ]]; then
  ENTRYPOINT="camera_server.py"
  shift
else
  ENTRYPOINT="camera_server.py"
fi

if command -v conda >/dev/null 2>&1; then
  (cd "${ROBOT_DIR}" && conda run -n "${ENV_NAME}" "${MJ_PYTHON}" "${ENTRYPOINT}" "$@")
else
  (cd "${ROBOT_DIR}" && "${MJ_PYTHON}" "${ENTRYPOINT}" "$@")
fi
