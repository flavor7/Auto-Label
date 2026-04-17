import argparse
import json
from pathlib import Path
from typing import Any


def normalize_path(value: str) -> str:
    return value.replace("\\", "/")


def iou_xywh(box_a: list[float], box_b: list[float]) -> float:
    ax, ay, aw, ah = box_a
    bx, by, bw, bh = box_b

    x1 = max(ax, bx)
    y1 = max(ay, by)
    x2 = min(ax + aw, bx + bw)
    y2 = min(ay + ah, by + bh)

    iw = max(0.0, x2 - x1)
    ih = max(0.0, y2 - y1)
    inter = iw * ih
    if inter <= 0:
        return 0.0

    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def resolve_image_id(record: dict[str, Any], image_id_by_name: dict[str, int]) -> int | None:
    keys: list[str] = []
    if record.get("image_rel_path"):
        keys.append(normalize_path(str(record["image_rel_path"])))
    if record.get("image_path"):
        raw = str(record["image_path"])
        keys.append(normalize_path(raw))
        keys.append(normalize_path(str(Path(raw).resolve())))

    for key in keys:
        if key in image_id_by_name:
            return image_id_by_name[key]
    return None


def evaluate_variant(
    name: str,
    records: list[dict[str, Any]],
    selected_image_ids: set[int],
    gt_annotations: list[dict[str, Any]],
    category_id_by_name: dict[str, int],
    category_name_by_id: dict[int, str],
    iou_threshold: float,
) -> dict[str, Any]:
    gt_map: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for ann in gt_annotations:
        if int(ann["image_id"]) in selected_image_ids:
            key = (int(ann["image_id"]), int(ann["category_id"]))
            gt_map.setdefault(key, []).append({"bbox": ann["bbox"], "matched": False})

    class_stats: dict[str, dict[str, int]] = {}
    for class_name in category_id_by_name:
        class_stats[class_name] = {"tp": 0, "fp": 0, "fn": 0}

    per_image: list[dict[str, Any]] = []
    tp = fp = 0

    for record in records:
        image_id = int(record["_resolved_image_id"])
        image_tp = image_fp = 0

        preds = sorted(record.get("predictions", []), key=lambda p: float(p.get("score") or 0.0), reverse=True)
        for pred in preds:
            label = str(pred["label"])
            if label not in category_id_by_name:
                continue
            category_id = category_id_by_name[label]
            pred_bbox = pred["bbox"]
            pred_xywh = [
                float(pred_bbox[0]),
                float(pred_bbox[1]),
                float(pred_bbox[2]) - float(pred_bbox[0]),
                float(pred_bbox[3]) - float(pred_bbox[1]),
            ]

            candidates = gt_map.get((image_id, category_id), [])
            best_iou = 0.0
            best_idx = -1
            for idx, candidate in enumerate(candidates):
                if candidate["matched"]:
                    continue
                score = iou_xywh(pred_xywh, candidate["bbox"])
                if score > best_iou:
                    best_iou = score
                    best_idx = idx

            if best_iou >= iou_threshold and best_idx >= 0:
                candidates[best_idx]["matched"] = True
                tp += 1
                image_tp += 1
                class_stats[label]["tp"] += 1
            else:
                fp += 1
                image_fp += 1
                class_stats[label]["fp"] += 1

        per_image.append(
            {
                "asset_id": record.get("asset_id", ""),
                "image_id": image_id,
                "pred_count": len(preds),
                "tp": image_tp,
                "fp": image_fp,
            }
        )

    fn = 0
    for (image_id, category_id), ann_list in gt_map.items():
        class_name = category_name_by_id[category_id]
        for ann in ann_list:
            if not ann["matched"]:
                fn += 1
                class_stats[class_name]["fn"] += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    avg_fp_per_image = fp / len(records) if records else 0.0

    gt_present_classes = sorted({category_name_by_id[int(a["category_id"])] for a in gt_annotations if int(a["image_id"]) in selected_image_ids})
    tp_hit_classes = sorted([name for name, stats in class_stats.items() if stats["tp"] > 0])
    predicted_classes = sorted({str(pred["label"]) for rec in records for pred in rec.get("predictions", [])})

    return {
        "name": name,
        "images": len(records),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "avg_fp_per_image": avg_fp_per_image,
        "gt_present_classes": gt_present_classes,
        "predicted_classes": predicted_classes,
        "tp_hit_classes": tp_hit_classes,
        "class_stats": class_stats,
        "per_image": per_image,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze class coverage for a selected subset.")
    parser.add_argument("--gt-coco", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--refinement-v1", required=True)
    parser.add_argument("--refinement-v2", default=None)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    gt = json.loads(Path(args.gt_coco).read_text(encoding="utf-8"))
    image_id_by_name = {normalize_path(str(im["file_name"])): int(im["id"]) for im in gt.get("images", [])}
    category_id_by_name = {str(c["name"]): int(c["id"]) for c in gt.get("categories", [])}
    category_name_by_id = {int(c["id"]): str(c["name"]) for c in gt.get("categories", [])}
    gt_annotations = gt.get("annotations", [])

    variants_spec = [("baseline", args.baseline), ("refinement_v1", args.refinement_v1)]
    if args.refinement_v2:
        variants_spec.append(("refinement_v2", args.refinement_v2))

    loaded: dict[str, list[dict[str, Any]]] = {}
    for name, path in variants_spec:
        records = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
        for record in records:
            resolved = resolve_image_id(record, image_id_by_name)
            if resolved is None:
                raise KeyError(f"Could not resolve image for variant={name} asset_id={record.get('asset_id')}")
            record["_resolved_image_id"] = resolved
        loaded[name] = records

    selected_image_ids = {int(r["_resolved_image_id"]) for r in loaded["baseline"]}

    results: dict[str, Any] = {
        "iou_threshold": args.iou_threshold,
        "variants": {},
    }

    for name in loaded:
        results["variants"][name] = evaluate_variant(
            name=name,
            records=loaded[name],
            selected_image_ids=selected_image_ids,
            gt_annotations=gt_annotations,
            category_id_by_name=category_id_by_name,
            category_name_by_id=category_name_by_id,
            iou_threshold=args.iou_threshold,
        )

    baseline_hit = set(results["variants"]["baseline"]["tp_hit_classes"])
    v1_hit = set(results["variants"]["refinement_v1"]["tp_hit_classes"])
    dropped_v1 = sorted(baseline_hit - v1_hit)

    summary: dict[str, Any] = {
        "gt_classes": results["variants"]["baseline"]["gt_present_classes"],
        "baseline_tp_hit_classes": sorted(baseline_hit),
        "refinement_v1_tp_hit_classes": sorted(v1_hit),
        "dropped_in_v1_vs_baseline": dropped_v1,
    }

    if "refinement_v2" in results["variants"]:
        v2_hit = set(results["variants"]["refinement_v2"]["tp_hit_classes"])
        summary["refinement_v2_tp_hit_classes"] = sorted(v2_hit)
        summary["dropped_in_v2_vs_baseline"] = sorted(baseline_hit - v2_hit)

    results["summary"] = summary

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    lines: list[str] = []
    lines.append("# class coverage analysis")
    lines.append("")
    lines.append(f"- IoU threshold for TP/FN matching: `{args.iou_threshold}`")
    lines.append(f"- GT classes in selected subset: `{', '.join(summary['gt_classes'])}`")
    lines.append(f"- Baseline TP-hit classes: `{', '.join(summary['baseline_tp_hit_classes'])}`")
    lines.append(f"- Refinement v1 TP-hit classes: `{', '.join(summary['refinement_v1_tp_hit_classes'])}`")
    lines.append(f"- Classes dropped in v1 vs baseline: `{', '.join(summary['dropped_in_v1_vs_baseline']) or 'none'}`")
    if "refinement_v2_tp_hit_classes" in summary:
        lines.append(f"- Refinement v2 TP-hit classes: `{', '.join(summary['refinement_v2_tp_hit_classes'])}`")
        lines.append(f"- Classes dropped in v2 vs baseline: `{', '.join(summary['dropped_in_v2_vs_baseline']) or 'none'}`")

    lines.append("")
    lines.append("## Variant metrics")
    lines.append("")
    for key in ("baseline", "refinement_v1", "refinement_v2"):
        if key not in results["variants"]:
            continue
        variant = results["variants"][key]
        lines.append(f"### {key}")
        lines.append(f"- TP/FP/FN: `{variant['tp']}/{variant['fp']}/{variant['fn']}`")
        lines.append(f"- Precision/Recall/F1: `{variant['precision']:.4f}/{variant['recall']:.4f}/{variant['f1']:.4f}`")
        lines.append(f"- Avg FP per image: `{variant['avg_fp_per_image']:.4f}`")
        lines.append("")

    output_md = Path(args.output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {output_json}")
    print(f"Wrote {output_md}")


if __name__ == "__main__":
    main()
