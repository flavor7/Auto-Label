# Linux GPU Deployment

## Recommended purchase setup

- GPU: `RTX 3090 24GB`
- Billing: start with hourly for smoke testing, then convert the same instance to monthly if the host is stable
- CPU / RAM: prefer at least `8 vCPU / 32GB RAM`
- Storage: keep the AutoDL local data disk at `>=100GB`; `150GB` is safer for this dataset plus checkpoints and outputs
- Image: choose an official PyTorch image with conda preinstalled; avoid a bare OS image for the first deployment

## Why this fits the repo

- The current project already has canonical manifest, export, and batch registration scripts
- The Linux mainline is moving to script-first execution instead of notebook-first execution
- The dataset currently occupies about `23GB`, so a small data disk will fill up quickly after adding checkpoints and exports

## Execution principles

- Use `deploy/linux/setup_env.sh` and `deploy/linux/start_stack.sh` as the default Linux entrypoints
- Keep notebooks only for experiments or one-off verification; they are not the Linux mainline
- Prefer config-driven and parameterized scripts so runs can be repeated and registered
- Target canonical `predictions.jsonl` output that can directly feed manifest / export / batch-register flows

## Suggested directory layout

```text
/root/autodl-tmp/
  inspecsafe/
    program/
    datasets/
    outputs/
```

Clone the repo under `/root/autodl-tmp/inspecsafe/program` and keep the dataset under `/root/autodl-tmp/inspecsafe/datasets`.

## Repo entrypoint

This branch keeps Linux GPU deployment assets under `deploy/linux/`.

For day-to-day instance handling and persistence strategy, also refer to `deploy/linux/AUTODL_USAGE.md`.

## Setup steps

```bash
cd /root/autodl-tmp/inspecsafe/program/inspecsafe_auto_label_tool
bash deploy/linux/setup_env.sh
```

## Start services

```bash
export ENV_NAME=inspecsafe-gpu
export DOCUMENT_ROOT=/root/autodl-tmp/inspecsafe/program
export DATA_ROOT=/root/autodl-tmp/inspecsafe/datasets/InspecSafe-V1/DATA_PATH
export LABEL_STUDIO_PORT=6006
export STATIC_PORT=6008
bash deploy/linux/start_stack.sh
```

For personal AutoDL accounts, the official docs say arbitrary public ports are not exposed by default. AutoDL maps instance ports `6006` and `6008` to public addresses, so the script defaults to those ports. If you do not use the mapped public addresses, use SSH tunneling instead.

## First checks

```bash
nvidia-smi
python --version
conda activate inspecsafe-gpu
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
python -c "from groundingdino.util.inference import Model; print('GroundingDINO OK')"
python -c "from segment_anything import sam_model_registry; print('SAM OK')"
```

## Notes

- AutoDL local disk is convenient, but it should not be your only backup for important data
- Keep a second copy of the dataset or outputs in object storage, AutoDL netdisk, or your local machine
- For long-running services, use `tmux` or AutoDL daemon mode in addition to `nohup` if you need stronger process persistence
