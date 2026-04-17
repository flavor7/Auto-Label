import argparse
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from inspecsafe_auto_label.indexing import load_jsonl, write_json, write_jsonl


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
    if union <= 0:
        return 0.0
    return inter_area / union


def nms(predictions: list[dict[str, Any]], iou_threshold: float) -> list[dict[str, Any]]:
    sorted_preds = sorted(predictions, key=lambda p: float(p.get("score") or 0.0), reverse=True)
    kept: list[dict[str, Any]] = []

    for pred in sorted_preds:
        should_keep = True
        for selected in kept:
            if bbox_iou_xyxy(pred["bbox"], selected["bbox"]) >= iou_threshold:
                should_keep = False
                break
        if should_keep:
            kept.append(pred)

    return kept


def refine_image_predictions(
    predictions: list[dict[str, Any]],
    default_min_score: float,
    pipeline_min_score: float,
    pipeline_topk: int,
    nms_iou: float,
) -> list[dict[str, Any]]:
    by_label: dict[str, list[dict[str, Any]]] = {}
    for pred in predictions:
        by_label.setdefault(pred["label"], []).append(pred)

    refined: list[dict[str, Any]] = []
    for label, items in by_label.items():
        sorted_items = sorted(items, key=lambda p: float(p.get("score") or 0.0), reverse=True)

        if label == "Pipeline":
            filtered = [item for item in sorted_items if float(item.get("score") or 0.0) >= pipeline_min_score]
            if pipeline_topk > 0:
                filtered = filtered[:pipeline_topk]
        else:
            filtered = [item for item in sorted_items if float(item.get("score") or 0.0) >= default_min_score]

        refined.extend(nms(filtered, iou_threshold=nms_iou))

    refined.sort(key=lambda p: float(p.get("score") or 0.0), reverse=True)
    return refined


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply minimal refinement heuristics to prediction JSONL.")
    parser.add_argument("--input", required=True, help="Input predictions.jsonl path.")
    parser.add_argument("--output", required=True, help="Output refined predictions.jsonl path.")
    parser.add_argument(
        "--summary-output",
        default=None,
        help="Optional summary json path. Defaults to sibling refine_summary.json of --output.",
    )
    parser.add_argument("--default-min-score", type=float, default=0.5, help="Default per-class minimum score.")
    parser.add_argument("--pipeline-min-score", type=float, default=0.35, help="Minimum score for Pipeline class.")
    parser.add_argument("--pipeline-topk", type=int, default=2, help="Keep at most top-K Pipeline predictions per image.")
    parser.add_argument("--nms-iou", type=float, default=0.7, help="Label-wise NMS IoU threshold.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    records = load_jsonl(args.input)
    refined_records: list[dict[str, Any]] = []

    total_before = 0
    total_after = 0

    for record in records:
        before_count = len(record.get("predictions", []))
        refined_predictions = refine_image_predictions(
            predictions=record.get("predictions", []),
            default_min_score=args.default_min_score,
            pipeline_min_score=args.pipeline_min_score,
            pipeline_topk=args.pipeline_topk,
            nms_iou=args.nms_iou,
        )
        after_count = len(refined_predictions)

        refined_record = dict(record)
        refined_record["predictions"] = refined_predictions
        refined_records.append(refined_record)

        total_before += before_count
        total_after += after_count

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
        "pipeline_min_score": args.pipeline_min_score,
        "pipeline_topk": args.pipeline_topk,
        "nms_iou": args.nms_iou,
    }
    write_json(summary, summary_path)

    print(f"Wrote refined predictions: {output_path}")
    print(f"Wrote refine summary: {summary_path}")


if __name__ == "__main__":
    main()
