#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_NAME="${ENV_NAME:-inspecsafe-gpu}"
HOST="${HOST:-0.0.0.0}"
LABEL_STUDIO_PORT="${LABEL_STUDIO_PORT:-6006}"
STATIC_PORT="${STATIC_PORT:-6008}"
DOCUMENT_ROOT="${DOCUMENT_ROOT:-$(cd "$PROJECT_ROOT/.." && pwd)}"
DATA_ROOT="${DATA_ROOT:-$DOCUMENT_ROOT/datasets/InspecSafe-V1/DATA_PATH}"
LOG_DIR="${LOG_DIR:-$PROJECT_ROOT/artifacts/logs}"

if [ ! -d "$DATA_ROOT" ]; then
  echo "[ERROR] DATA_ROOT not found: $DATA_ROOT"
  exit 1
fi

if ! command -v conda >/dev/null 2>&1; then
  echo "[ERROR] conda not found."
  exit 1
fi

mkdir -p "$LOG_DIR"
eval "$(conda shell.bash hook)"
conda activate "$ENV_NAME"

STATIC_LOG="$LOG_DIR/static_server.log"
LABEL_LOG="$LOG_DIR/label_studio.log"

pkill -f "run_static_server_with_cors.py --root $DATA_ROOT" >/dev/null 2>&1 || true
pkill -f "label-studio --host $HOST --port $LABEL_STUDIO_PORT" >/dev/null 2>&1 || true

nohup python "$PROJECT_ROOT/scripts/run_static_server_with_cors.py" \
  --root "$DATA_ROOT" \
  --host "$HOST" \
  --port "$STATIC_PORT" \
  --allow-origin "*" >"$STATIC_LOG" 2>&1 &

export LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED=true
export LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT="$DOCUMENT_ROOT"
export NO_PROXY="localhost,127.0.0.1"

nohup label-studio --host "$HOST" --port "$LABEL_STUDIO_PORT" >"$LABEL_LOG" 2>&1 &

echo "[OK] Started services"
echo "  Label Studio: http://$HOST:$LABEL_STUDIO_PORT"
echo "  Static files: http://$HOST:$STATIC_PORT"
echo "  Logs:         $LOG_DIR"
