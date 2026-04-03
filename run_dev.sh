#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  local exit_code=$?

  trap - EXIT INT TERM

  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi

  if [[ -n "${FRONTEND_PID}" ]] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi

  wait "${BACKEND_PID}" "${FRONTEND_PID}" 2>/dev/null || true
  exit "${exit_code}"
}

trap cleanup EXIT INT TERM

source "${HOME}/opensdlc-venv/bin/activate"

echo "[OpenSDLC] Starting backend on http://localhost:8000"
(
  cd "${ROOT_DIR}/backend"
  python run_server.py --reload
) &
BACKEND_PID=$!

echo "[OpenSDLC] Starting frontend on http://localhost:5173"
(
  cd "${ROOT_DIR}/frontend"
  npm run dev
) &
FRONTEND_PID=$!

wait -n "${BACKEND_PID}" "${FRONTEND_PID}"
