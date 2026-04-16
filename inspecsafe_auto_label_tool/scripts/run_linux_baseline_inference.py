import argparse
import json
import os
import re
from dataclasses import asdict
from pathlib import Path
import sys
from typing import Any

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from groundingdino.util.inference import Model
from segment_anything import SamPredictor, sam_model_registry

from inspecsafe_auto_label.indexing import load_jsonl, write_json, write_jsonl
from inspecsafe_auto_label.types import ImagePrediction, InstancePrediction


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def resolve_path(project_root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root / path


def resolve_local_bert_path(project_root: Path) -> Path:
    local_bert_raw = os.environ.get("INSPECSAFE_LOCAL_BERT_PATH")
    candidate = Path(local_bert_raw) if local_bert_raw else (project_root / "bert-base-uncased")
    if not candidate.is_absolute():
        candidate = project_root / candidate

    resolved = candidate.resolve()
    if not resolved.is_dir():
        raise FileNotFoundError(f"Local BERT directory not found: {resolved}")
    if not (resolved / "config.json").is_file():
        raise FileNotFoundError(f"Local BERT directory missing config.json: {resolved}")
    return resolved


def build_gdino_config_with_local_bert(model_config_path: Path, local_bert_path: Path, runtime_dir: Path) -> Path:
    config_text = model_config_path.read_text(encoding="utf-8")
    pattern = r'(?m)^text_encoder_type\s*=\s*["\'][^"\']+["\']\s*$'
    replacement = f'text_encoder_type = "{local_bert_path.as_posix()}"'

    if not re.search(pattern, config_text):
        raise ValueError(f"text_encoder_type not found in GroundingDINO config: {model_config_path}")

    patched_text = re.sub(pattern, replacement, config_text, count=1)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    patched_path = runtime_dir / f"{model_config_path.stem}.local_bert.py"
    patched_path.write_text(patched_text, encoding="utf-8")
    return patched_path


def load_label_specs(label_schema_path: str | Path) -> list[dict[str, str]]:
    payload = load_json(label_schema_path)
    specs: list[dict[str, str]] = []
    for item in payload.get("labels", []):
        prompts = item.get("prompts") or []
        if not prompts:
            continue
        specs.append({"canonical_name": item["name"], "prompt": prompts[0]})
    return specs


def mask_to_polygon(mask: np.ndarray) -> list[list[float]]:
    mask_uint8 = (mask.astype(np.uint8)) * 255
    contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return []

    contour = max(contours, key=cv2.contourArea)
    epsilon = 0.002 * cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, epsilon, True)
    polygon = [[float(point[0][0]), float(point[0][1])] for point in approx]
    return polygon if len(polygon) >= 3 else []


def build_predictions_for_image(
    image_path: Path,
    asset: dict[str, Any],
    label_specs: list[dict[str, str]],
    gdino_model: Model,
    sam_predictor: SamPredictor,
    box_threshold: float,
    text_threshold: float,
) -> ImagePrediction:
    image_bgr = cv2.imread(str(image_path))
    if image_bgr is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    sam_predictor.set_image(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
    instances: list[InstancePrediction] = []

    for label_spec in label_specs:
        detections, _labels = gdino_model.predict_with_caption(
            image=image_bgr,
            caption=f"{label_spec['prompt']} .",
            box_threshold=box_threshold,
            text_threshold=text_threshold,
        )

        if detections.xyxy is None or len(detections.xyxy) == 0:
            continue

        confidences = detections.confidence if detections.confidence is not None else [None] * len(detections.xyxy)
        for box, score in zip(detections.xyxy, confidences):
            x1, y1, x2, y2 = [float(value) for value in box.tolist()]
            masks, _scores, _logits = sam_predictor.predict(
                box=np.array([x1, y1, x2, y2]),
                multimask_output=False,
            )
            polygon = mask_to_polygon(masks[0]) if len(masks) else []
            instances.append(
                InstancePrediction(
                    label=label_spec["canonical_name"],
                    score=None if score is None else float(score),
                    bbox=[x1, y1, x2, y2],
                    polygon=polygon,
                )
            )

    return ImagePrediction(
        image_path=str(image_path.resolve()),
        image_rel_path=asset["image_rel_path"],
        width=int(asset["width"]),
        height=int(asset["height"]),
        predictions=instances,
        asset_id=asset["asset_id"],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Linux baseline inference pipeline.")
    parser.add_argument("--config", default="configs/linux_inference.default.json", help="JSON config path.")
    parser.add_argument("--dataset-root", default=None, help="Override dataset root.")
    parser.add_argument("--output-dir", default=None, help="Override output directory.")
    parser.add_argument("--split", default=None, help="Override split filter.")
    parser.add_argument("--subset", default=None, help="Override subset filter.")
    parser.add_argument("--task-group-id", default=None, help="Override task group filter.")
    parser.add_argument("--limit", type=int, default=None, help="Override limit.")
    parser.add_argument("--offset", type=int, default=None, help="Override offset within selected assets.")
    parser.add_argument("--asset-id", action="append", default=None, help="Optional asset_id filter, repeatable.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_json(resolve_path(PROJECT_ROOT, args.config))

    dataset_root = resolve_path(PROJECT_ROOT, args.dataset_root or config["dataset_root"])
    asset_manifest_path = resolve_path(PROJECT_ROOT, config["asset_manifest"])
    label_schema_path = resolve_path(PROJECT_ROOT, config["label_schema"])
    output_dir = resolve_path(PROJECT_ROOT, args.output_dir or config["output_dir"])

    split_filter = args.split if args.split is not None else config.get("split")
    subset_filter = args.subset if args.subset is not None else config.get("subset")
    task_group_filter = args.task_group_id if args.task_group_id is not None else config.get("task_group_id")
    asset_ids = args.asset_id if args.asset_id is not None else list(config.get("asset_ids") or [])
    limit = args.limit if args.limit is not None else int(config.get("limit", 0) or 0)
    offset = args.offset if args.offset is not None else int(config.get("offset", 0) or 0)
    if offset < 0:
        raise ValueError("offset must be >= 0")

    model_config = config["model"]
    threshold_config = config["thresholds"]
    export_config = config["export"]

    if not export_config.get("write_predictions_jsonl", False):
        raise ValueError("This baseline script only supports write_predictions_jsonl=true.")

    gdino_config_path = resolve_path(PROJECT_ROOT, model_config["groundingdino_config"])
    gdino_checkpoint_path = resolve_path(PROJECT_ROOT, model_config["groundingdino_checkpoint"])
    sam_checkpoint_path = resolve_path(PROJECT_ROOT, model_config["sam_checkpoint"])
    local_bert_path = resolve_local_bert_path(PROJECT_ROOT)
    gdino_runtime_config_path = build_gdino_config_with_local_bert(
        model_config_path=gdino_config_path,
        local_bert_path=local_bert_path,
        runtime_dir=output_dir / ".runtime",
    )
    print(f"[INFO] local_bert_path: {local_bert_path}")
    print(f"[INFO] gdino_runtime_config: {gdino_runtime_config_path}")
    device = model_config["device"]
    sam_model_type = model_config["sam_model_type"]
    box_threshold = float(threshold_config["box_threshold"])
    text_threshold = float(threshold_config["text_threshold"])

    label_specs = load_label_specs(label_schema_path)
    asset_records = load_jsonl(asset_manifest_path)

    if split_filter:
        asset_records = [record for record in asset_records if record.get("split") == split_filter]
    if subset_filter:
        asset_records = [record for record in asset_records if record.get("subset") == subset_filter]
    if task_group_filter:
        asset_records = [record for record in asset_records if record.get("task_group_id") == task_group_filter]
    if asset_ids:
        allowed_asset_ids = set(asset_ids)
        asset_records = [record for record in asset_records if record.get("asset_id") in allowed_asset_ids]

    if offset > 0:
        asset_records = asset_records[offset:]
    if limit > 0:
        asset_records = asset_records[:limit]

    selected_count = len(asset_records)
    if selected_count == 0:
        raise ValueError("No asset records selected for inference.")

    print(
        f"[INFO] batch selection split={split_filter} offset={offset} limit={limit} selected_count={selected_count}",
        flush=True,
    )

    gdino_model = Model(
        model_config_path=str(gdino_runtime_config_path),
        model_checkpoint_path=str(gdino_checkpoint_path),
        device=device,
    )
    sam = sam_model_registry[sam_model_type](checkpoint=str(sam_checkpoint_path))
    sam.to(device=device)
    sam_predictor = SamPredictor(sam)

    outputs: list[dict[str, Any]] = []
    success_count = 0
    failure_count = 0

    for index, asset in enumerate(asset_records, start=1):
        asset_id = asset["asset_id"]
        image_path = dataset_root / Path(asset["image_rel_path"])
        try:
            prediction = build_predictions_for_image(
                image_path=image_path,
                asset=asset,
                label_specs=label_specs,
                gdino_model=gdino_model,
                sam_predictor=sam_predictor,
                box_threshold=box_threshold,
                text_threshold=text_threshold,
            )
            outputs.append(asdict(prediction))
            success_count += 1
            print(
                f"progress {index}/{selected_count} asset_id={asset_id} success={success_count} failure={failure_count} predictions={len(prediction.predictions)}",
                flush=True,
            )
        except Exception as exc:
            failure_count += 1
            print(
                f"progress {index}/{selected_count} asset_id={asset_id} success={success_count} failure={failure_count} status=failed error={type(exc).__name__}: {exc}",
                flush=True,
            )

    output_path = output_dir / "predictions.jsonl"
    write_jsonl(outputs, output_path)

    processed_count = success_count + failure_count
    run_summary = {
        "split": split_filter,
        "offset": offset,
        "limit": limit,
        "selected_count": selected_count,
        "processed_count": processed_count,
        "success_count": success_count,
        "failure_count": failure_count,
        "output_dir": str(output_dir.resolve()),
    }
    run_summary_path = output_dir / "run_summary.json"
    write_json(run_summary, run_summary_path)

    print(f"wrote {len(outputs)} records to {output_path}")
    print(f"wrote run summary to {run_summary_path}")


if __name__ == "__main__":
    main()
