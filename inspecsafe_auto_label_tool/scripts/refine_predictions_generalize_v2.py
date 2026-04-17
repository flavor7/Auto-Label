import argparse
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from inspecsafe_auto_label.indexing import load_jsonl, write_json, write_jsonl
from refine_predictions_generalize_v1 import filter_by_label_rules


FIRE_HYDRANT_RESCUE_SOURCE_LABELS = {"Electrical Box"}
FIRE_HYDRANT_RESCUE_MIN_SCORE = 0.39
FIRE_HYDRANT_RESCUE_RATIO_RANGE = (0.54, 0.60)
FIRE_HYDRANT_RESCUE_AREA_RANGE = (90000.0, 110000.0)


def bbox_area(prediction: dict[str, Any]) -> float:
    x1, y1, x2, y2 = prediction["bbox"]
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def bbox_ratio(prediction: dict[str, Any]) -> float:
    x1, y1, x2, y2 = prediction["bbox"]
    width = max(0.0, x2 - x1)
    height = max(0.0, y2 - y1)
    return width / height if height > 0 else 0.0


def is_fire_hydrant_rescue_candidate(prediction: dict[str, Any]) -> bool:
    label = str(prediction["label"])
    if label not in FIRE_HYDRANT_RESCUE_SOURCE_LABELS:
        return False

    score = float(prediction.get("score") or 0.0)
    if score < FIRE_HYDRANT_RESCUE_MIN_SCORE:
        return False

    ratio = bbox_ratio(prediction)
    area = bbox_area(prediction)
    return (
        FIRE_HYDRANT_RESCUE_RATIO_RANGE[0] <= ratio <= FIRE_HYDRANT_RESCUE_RATIO_RANGE[1]
        and FIRE_HYDRANT_RESCUE_AREA_RANGE[0] <= area <= FIRE_HYDRANT_RESCUE_AREA_RANGE[1]
    )


def keep_native_fire_hydrant(prediction: dict[str, Any]) -> bool:
    score = float(prediction.get("score") or 0.0)
    if score < FIRE_HYDRANT_RESCUE_MIN_SCORE:
        return False

    ratio = bbox_ratio(prediction)
    area = bbox_area(prediction)
    return (
        FIRE_HYDRANT_RESCUE_RATIO_RANGE[0] <= ratio <= FIRE_HYDRANT_RESCUE_RATIO_RANGE[1]
        and FIRE_HYDRANT_RESCUE_AREA_RANGE[0] <= area <= FIRE_HYDRANT_RESCUE_AREA_RANGE[1]
    )


def apply_high_fn_rescue(
    raw_predictions: list[dict[str, Any]],
    v1_predictions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    refined = [
        pred
        for pred in v1_predictions
        if pred["label"] != "Fire Hydrant" or keep_native_fire_hydrant(pred)
    ]

    removed_native_fire_hydrant = sum(1 for pred in v1_predictions if pred["label"] == "Fire Hydrant") - sum(
        1 for pred in refined if pred["label"] == "Fire Hydrant"
    )

    added_fire_hydrant_rescues = 0
    for pred in raw_predictions:
        if not is_fire_hydrant_rescue_candidate(pred):
            continue
        refined.append(
            {
                "label": "Fire Hydrant",
                "score": pred["score"],
                "bbox": pred["bbox"],
            }
        )
        added_fire_hydrant_rescues += 1

    refined.sort(key=lambda pred: float(pred.get("score") or 0.0), reverse=True)
    return refined, {
        "removed_native_fire_hydrant": removed_native_fire_hydrant,
        "added_fire_hydrant_rescues": added_fire_hydrant_rescues,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply generalization-oriented refinement v2 with targeted high-FN rescue.")
    parser.add_argument("--input", required=True, help="Input baseline predictions.jsonl path.")
    parser.add_argument("--output", required=True, help="Output refined predictions.jsonl path.")
    parser.add_argument("--summary-output", default=None, help="Optional summary json path.")
    parser.add_argument("--default-min-score", type=float, default=0.35)
    parser.add_argument("--nms-iou", type=float, default=0.6)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    records = load_jsonl(args.input)
    refined_records: list[dict[str, Any]] = []

    total_before = 0
    total_after = 0
    rescue_totals = {
        "removed_native_fire_hydrant": 0,
        "added_fire_hydrant_rescues": 0,
    }
    kept_by_label: dict[str, int] = {}
    removed_by_label: dict[str, int] = {}

    for record in records:
        raw_predictions = list(record.get("predictions", []))
        v1_predictions = filter_by_label_rules(
            predictions=raw_predictions,
            default_min_score=args.default_min_score,
            nms_iou=args.nms_iou,
        )
        v2_predictions, rescue_counts = apply_high_fn_rescue(
            raw_predictions=raw_predictions,
            v1_predictions=v1_predictions,
        )

        for key, value in rescue_counts.items():
            rescue_totals[key] += value

        before_counts: dict[str, int] = {}
        after_counts: dict[str, int] = {}
        for pred in raw_predictions:
            label = str(pred["label"])
            before_counts[label] = before_counts.get(label, 0) + 1
        for pred in v2_predictions:
            label = str(pred["label"])
            after_counts[label] = after_counts.get(label, 0) + 1
            kept_by_label[label] = kept_by_label.get(label, 0) + 1

        for label, count in before_counts.items():
            removed_by_label[label] = removed_by_label.get(label, 0) + count - after_counts.get(label, 0)

        refined_record = dict(record)
        refined_record["predictions"] = v2_predictions
        refined_records.append(refined_record)

        total_before += len(raw_predictions)
        total_after += len(v2_predictions)

    output_path = Path(args.output)
    write_jsonl(refined_records, output_path)

    summary_path = Path(args.summary_output) if args.summary_output else output_path.with_name("refine_summary.json")
    summary = {
        "input_path": str(Path(args.input).resolve()),
        "output_path": str(output_path.resolve()),
        "records": len(refined_records),
        "predictions_before": total_before,
        "predictions_after": total_after,
        "removed": total_before - total_after,
        "base_refinement": "generalize_v1",
        "default_min_score": args.default_min_score,
        "nms_iou": args.nms_iou,
        "targeted_high_fn_strategy": {
            "focus_classes": ["Fire Hydrant", "Valve", "Pipeline", "Pressure Gauge"],
            "implemented_rescue": {
                "target_label": "Fire Hydrant",
                "source_labels": sorted(FIRE_HYDRANT_RESCUE_SOURCE_LABELS),
                "source_min_score": FIRE_HYDRANT_RESCUE_MIN_SCORE,
                "aspect_ratio_range": list(FIRE_HYDRANT_RESCUE_RATIO_RANGE),
                "area_range": list(FIRE_HYDRANT_RESCUE_AREA_RANGE),
                "native_fire_hydrant_policy": "drop giant native Fire Hydrant boxes that do not match the rescue geometry envelope",
            },
        },
        "rescue_totals": rescue_totals,
        "kept_by_label": dict(sorted(kept_by_label.items())),
        "removed_by_label": dict(sorted(removed_by_label.items())),
    }
    write_json(summary, summary_path)

    print(f"Wrote refined predictions: {output_path}")
    print(f"Wrote refine summary: {summary_path}")


if __name__ == "__main__":
    main()
