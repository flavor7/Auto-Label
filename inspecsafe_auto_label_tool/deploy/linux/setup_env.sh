#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_NAME="${ENV_NAME:-inspecsafe-gpu}"
PYTHON_VERSION="${PYTHON_VERSION:-3.10}"
THIRD_PARTY_DIR="${INSPECSAFE_THIRD_PARTY:-$PROJECT_ROOT/third_party}"
MODELS_DIR="${INSPECSAFE_MODELS_DIR:-$PROJECT_ROOT/models}"
TORCH_INDEX_URL="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu124}"

if ! command -v conda >/dev/null 2>&1; then
  echo "[ERROR] conda not found. Use an AutoDL image with conda preinstalled."
  exit 1
fi

eval "$(conda shell.bash hook)"

if ! conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  echo "[INFO] Creating conda env: $ENV_NAME"
  conda create -n "$ENV_NAME" "python=$PYTHON_VERSION" -y
fi

conda activate "$ENV_NAME"

echo "[INFO] Installing Python dependencies"
python -m pip install -U pip setuptools wheel ninja
python -m pip install torch torchvision --index-url "$TORCH_INDEX_URL"
python -m pip install -U Pillow opencv-python pycocotools supervision label-studio

mkdir -p "$THIRD_PARTY_DIR" "$MODELS_DIR"

if [ ! -d "$THIRD_PARTY_DIR/GroundingDINO/.git" ]; then
  git clone https://github.com/IDEA-Research/GroundingDINO.git "$THIRD_PARTY_DIR/GroundingDINO"
fi

if [ ! -d "$THIRD_PARTY_DIR/segment-anything/.git" ]; then
  git clone https://github.com/facebookresearch/segment-anything.git "$THIRD_PARTY_DIR/segment-anything"
fi

echo "[INFO] Installing Segment Anything"
python -m pip install -e "$THIRD_PARTY_DIR/segment-anything"

echo "[INFO] Installing GroundingDINO"
export AM_I_DOCKER=False
export BUILD_WITH_CUDA=True
export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
python -m pip install --no-build-isolation -e "$THIRD_PARTY_DIR/GroundingDINO"

if [ ! -f "$MODELS_DIR/groundingdino_swint_ogc.pth" ]; then
  wget -O "$MODELS_DIR/groundingdino_swint_ogc.pth" \
    https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth
fi

if [ ! -f "$MODELS_DIR/sam_vit_b_01ec64.pth" ]; then
  wget -O "$MODELS_DIR/sam_vit_b_01ec64.pth" \
    https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth
fi

echo "[OK] AutoDL environment is ready."
echo "  env:    $ENV_NAME"
echo "  code:   $PROJECT_ROOT"
echo "  models: $MODELS_DIR"
