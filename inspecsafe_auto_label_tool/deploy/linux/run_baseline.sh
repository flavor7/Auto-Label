#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_NAME="${ENV_NAME:-inspecsafe-gpu}"
CODE_ROOT="${INSPECSAFE_CODE_ROOT:-$PROJECT_ROOT}"
RESOURCE_ROOT="${INSPECSAFE_RESOURCE_ROOT:-/root/autodl-tmp/inspecsafe/program/inspecsafe_auto_label_tool}"
DATASET_ROOT="${INSPECSAFE_DATASET_ROOT:-/root/autodl-tmp/datasets/InspecSafe-V1/DATA_PATH}"
CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
BERT_LINK_PATH="${INSPECSAFE_BERT_LINK_PATH:-$(cd "$CODE_ROOT/.." && pwd)/bert-base-uncased}"
BERT_SOURCE_PATH="${INSPECSAFE_BERT_SOURCE_PATH:-$RESOURCE_ROOT/bert-base-uncased}"
BASELINE_SCRIPT="$CODE_ROOT/scripts/run_linux_baseline_inference.py"
DEFAULT_CONFIG="${INSPECSAFE_BASELINE_CONFIG:-$CODE_ROOT/configs/linux_inference.default.json}"

if ! command -v conda >/dev/null 2>&1; then
  echo "[ERROR] conda not found."
  exit 1
fi

if [ ! -d "$DATASET_ROOT" ]; then
  echo "[ERROR] dataset root not found: $DATASET_ROOT"
  exit 1
fi

if [ ! -d "$RESOURCE_ROOT" ]; then
  echo "[ERROR] resource root not found: $RESOURCE_ROOT"
  exit 1
fi

if [ ! -d "$BERT_SOURCE_PATH" ]; then
  echo "[ERROR] local bert directory not found: $BERT_SOURCE_PATH"
  exit 1
fi

if [ ! -f "$RESOURCE_ROOT/third_party/GroundingDINO/groundingdino/_C.cpython-312-x86_64-linux-gnu.so" ]; then
  echo "[ERROR] GroundingDINO _C extension not found under resource root."
  echo "        expected: $RESOURCE_ROOT/third_party/GroundingDINO/groundingdino/_C.cpython-312-x86_64-linux-gnu.so"
  exit 1
fi

mkdir -p "$(dirname "$BERT_LINK_PATH")"
ln -sfn "$BERT_SOURCE_PATH" "$BERT_LINK_PATH"

source "/root/miniconda3/etc/profile.d/conda.sh"
conda activate "$ENV_NAME"

export CUDA_HOME
export PYTHONPATH="$RESOURCE_ROOT/third_party/GroundingDINO:$RESOURCE_ROOT/third_party/segment-anything:$CODE_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

echo "[INFO] env:          $ENV_NAME"
echo "[INFO] python:       $(command -v python)"
echo "[INFO] dataset_root: $DATASET_ROOT"
echo "[INFO] resource:     $RESOURCE_ROOT"
echo "[INFO] bert link:    $BERT_LINK_PATH -> $(readlink -f "$BERT_LINK_PATH")"
echo "[INFO] config:       $DEFAULT_CONFIG"

exec python "$BASELINE_SCRIPT" \
  --config "$DEFAULT_CONFIG" \
  --dataset-root "$DATASET_ROOT" \
  "$@"
