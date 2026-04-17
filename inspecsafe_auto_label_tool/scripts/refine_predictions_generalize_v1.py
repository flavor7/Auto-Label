import argparse
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from inspecsafe_auto_label.indexing import load_jsonl, write_json, write_jsonl


CLASS_MIN_SCORE: dict[str, float] = {
    "Electronic Control Cabinet": 0.70,
    "Ladder": 0.65,
    "Direct-Blow Pipe": 0.52,
    "Sight Hole Cover": 0.50,
    "Electrical Box": 0.38,
    "Safety Helmet": 0.46,
    "Motor": 0.395,
}

TOPK_BY_LABEL: dict[str, int] = {
    "Electronic Control Cabinet": 1,
    "Ladder": 1,
    "Direct-Blow Pipe": 1,
    "Sight Hole Cover": 1,
    "Electrical Box": 3,
    "Safety Helmet": 2,
}

ELECTRICAL_BOX_RATIO_RANGE = (0.38, 0.50)
ELECTRICAL_BOX_AREA_RANGE = (120000.0, 200000.0)


def bbox_iou_xyxy(box_a: list[float], box_b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area <= 0:
        return 0.0

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area
    return inter_area / union if union > 0 else 0.0


def nms(predictions: list[dict[str, Any]], iou_threshold: float) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for pred in sorted(predictions, key=lambda p: float(p.get("score") or 0.0), reverse=True):
        if all(bbox_iou_xyxy(pred["bbox"], selected["bbox"]) < iou_threshold for selected in kept):
            kept.append(pred)
    return kept


def passes_geometry_guard(label: str, prediction: dict[str, Any]) -> bool:
    if label != "Electrical Box":
        return True

    x1, y1, x2, y2 = prediction["bbox"]
    width = max(0.0, x2 - x1)
    height = max(0.0, y2 - y1)
    if width <= 0 or height <= 0:
        return False

    aspect_ratio = width / height
    area = width * height

    # Keep only cabinet-like boxes for Electrical Box to avoid large-scene
    # confusion and small-object clutter while preserving the observed GT hits.
    return (
        ELECTRICAL_BOX_RATIO_RANGE[0] <= aspect_ratio <= ELECTRICAL_BOX_RATIO_RANGE[1]
        and ELECTRICAL_BOX_AREA_RANGE[0] <= area <= ELECTRICAL_BOX_AREA_RANGE[1]
    )


def suppress_pair(
    predictions: list[dict[str, Any]],
    primary_label: str,
    secondary_label: str,
    iou_threshold: float,
) -> list[dict[str, Any]]:
    primary = [pred for pred in predictions if pred["label"] == primary_label]
    secondary = [pred for pred in predictions if pred["label"] == secondary_label]
    removed_ids: set[int] = set()

    for keep in primary:
        for drop in secondary:
            if bbox_iou_xyxy(keep["bbox"], drop["bbox"]) >= iou_threshold:
                removed_ids.add(id(drop))

    return [pred for pred in predictions if id(pred) not in removed_ids]


def filter_by_label_rules(
    predictions: list[dict[str, Any]],
    default_min_score: float,
    nms_iou: float,
) -> list[dict[str, Any]]:
    by_label: dict[str, list[dict[str, Any]]] = {}
    for pred in predictions:
        by_label.setdefault(str(pred["label"]), []).append(pred)

    refined: list[dict[str, Any]] = []
    for label, items in by_label.items():
        min_score = CLASS_MIN_SCORE.get(label, default_min_score)
        filtered = [item for item in items if float(item.get("score") or 0.0) >= min_score]
        filtered = nms(filtered, iou_threshold=nms_iou)
        filtered = [item for item in filtered if passes_geometry_guard(label, item)]

        topk = TOPK_BY_LABEL.get(label)
        if topk is not None:
            filtered = sorted(filtered, key=lambda p: float(p.get("score") or 0.0), reverse=True)[:topk]

        refined.extend(filtered)

    refined = suppress_pair(refined, primary_label="Pipeline", secondary_label="Direct-Blow Pipe", iou_threshold=0.7)
    refined = suppress_pair(refined, primary_label="Pressure Gauge", secondary_label="Sight Hole Cover", iou_threshold=0.65)
    refined = suppress_pair(refined, primary_label="Electrical Box", secondary_label="Electronic Control Cabinet", iou_threshold=0.65)

    refined.sort(key=lambda p: float(p.get("score") or 0.0), reverse=True)
    return refined


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply generalization-oriented refinement v1 to prediction JSONL.")
    parser.add_argument("--input", required=True, help="Input predictions.jsonl path.")
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
    removed_by_label: dict[str, int] = {}
    kept_by_label: dict[str, int] = {}

    for record in records:
        before_predictions = list(record.get("predictions", []))
        after_predictions = filter_by_label_rules(
            predictions=before_predictions,
            default_min_score=args.default_min_score,
            nms_iou=args.nms_iou,
        )

        before_counts: dict[str, int] = {}
        after_counts: dict[str, int] = {}
        for pred in before_predictions:
            label = str(pred["label"])
            before_counts[label] = before_counts.get(label, 0) + 1
        for pred in after_predictions:
            label = str(pred["label"])
            after_counts[label] = after_counts.get(label, 0) + 1
            kept_by_label[label] = kept_by_label.get(label, 0) + 1

        for label, count in before_counts.items():
            removed_by_label[label] = removed_by_label.get(label, 0) + count - after_counts.get(label, 0)

        refined_record = dict(record)
        refined_record["predictions"] = after_predictions
        refined_records.append(refined_record)

        total_before += len(before_predictions)
        total_after += len(after_predictions)

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
        "default_min_score": args.default_min_score,
        "class_min_score": CLASS_MIN_SCORE,
        "topk_by_label": TOPK_BY_LABEL,
        "geometry_guards": {
            "Electrical Box": {
                "aspect_ratio_range": list(ELECTRICAL_BOX_RATIO_RANGE),
                "area_range": list(ELECTRICAL_BOX_AREA_RANGE),
            }
        },
        "nms_iou": args.nms_iou,
        "cross_label_rules": [
            "Pipeline vs Direct-Blow Pipe: IoU>=0.7 keep Pipeline",
            "Pressure Gauge vs Sight Hole Cover: IoU>=0.65 keep Pressure Gauge",
            "Electrical Box vs Electronic Control Cabinet: IoU>=0.65 keep Electrical Box",
        ],
        "kept_by_label": dict(sorted(kept_by_label.items())),
        "removed_by_label": dict(sorted(removed_by_label.items())),
    }
    write_json(summary, summary_path)

    print(f"Wrote refined predictions: {output_path}")
    print(f"Wrote refine summary: {summary_path}")


if __name__ == "__main__":
    main()
