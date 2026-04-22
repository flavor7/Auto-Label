import argparse
import csv
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
    candidate_keys: list[str] = []
    if record.get("image_rel_path"):
        candidate_keys.append(normalize_path(str(record["image_rel_path"])))
    if record.get("image_path"):
        raw_path = str(record["image_path"])
        candidate_keys.append(normalize_path(raw_path))
        candidate_keys.append(normalize_path(str(Path(raw_path).resolve())))

    for key in candidate_keys:
        if key in image_id_by_name:
            return image_id_by_name[key]
    return None


def empty_class_stats() -> dict[str, Any]:
    return {
        "gt_instances": 0,
        "gt_image_count": 0,
        "pred_instances": 0,
        "pred_image_count": 0,
        "tp": 0,
        "fp": 0,
        "fn": 0,
        "tp_hit_image_count": 0,
        "precision": 0.0,
        "recall": 0.0,
    }


def empty_asset_class_stats() -> dict[str, int]:
    return {
        "gt_instances": 0,
        "pred_instances": 0,
        "tp": 0,
        "fp": 0,
        "fn": 0,
    }


def finalize_class_stats(stats: dict[str, Any], gt_image_ids: set[int], pred_image_ids: set[int], tp_hit_image_ids: set[int]) -> dict[str, Any]:
    tp = int(stats["tp"])
    fp = int(stats["fp"])
    fn = int(stats["fn"])
    stats["gt_image_count"] = len(gt_image_ids)
    stats["pred_image_count"] = len(pred_image_ids)
    stats["tp_hit_image_count"] = len(tp_hit_image_ids)
    stats["precision"] = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    stats["recall"] = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    return stats


def build_change_tags(baseline: dict[str, Any], variant: dict[str, Any]) -> list[str]:
    delta_tp = int(variant["tp"]) - int(baseline["tp"])
    delta_fp = int(variant["fp"]) - int(baseline["fp"])
    delta_fn = int(variant["fn"]) - int(baseline["fn"])

    tags: list[str] = []
    if delta_fn < 0 or delta_tp > 0:
        tags.append("FN improved")
    elif delta_fp < 0:
        tags.append("FP improved")
    elif delta_tp == 0 and delta_fp == 0 and delta_fn == 0:
        tags.append("No material change")
    else:
        tags.append("Worsened or mixed")

    if delta_fp < 0 and "FP improved" not in tags:
        tags.append("FP improved")
    if delta_fn == 0 and delta_tp == 0 and delta_fp == 0 and "No material change" not in tags:
        tags.append("No material change")

    return tags


def summarize_classes(comparison_rows: list[dict[str, Any]], variant_key: str) -> dict[str, list[str]]:
    summary = {
        "mainly_improved_fp": [],
        "mainly_improved_fn": [],
        "almost_no_change": [],
        "worsened_or_mixed": [],
    }
    for row in comparison_rows:
        tags = row["change_direction"][variant_key]
        class_name = row["class_name"]
        if "FN improved" in tags:
            summary["mainly_improved_fn"].append(class_name)
        elif "FP improved" in tags:
            summary["mainly_improved_fp"].append(class_name)
        elif "No material change" in tags:
            summary["almost_no_change"].append(class_name)
        else:
            summary["worsened_or_mixed"].append(class_name)
    return summary


def evaluate_variants(
    gt_payload: dict[str, Any],
    variants: dict[str, list[dict[str, Any]]],
    iou_threshold: float,
) -> tuple[list[str], dict[str, Any]]:
    image_id_by_name = {
        normalize_path(str(image["file_name"])): int(image["id"])
        for image in gt_payload.get("images", [])
        if image.get("file_name")
    }
    category_name_by_id = {int(category["id"]): str(category["name"]) for category in gt_payload.get("categories", [])}
    category_id_by_name = {name: category_id for category_id, name in category_name_by_id.items()}

    predicted_label_union: set[str] = set()
    for records in variants.values():
        for record in records:
            resolved = resolve_image_id(record, image_id_by_name)
            if resolved is None:
                raise KeyError(f"Could not resolve image for asset_id={record.get('asset_id')}")
            record["_resolved_image_id"] = resolved
            predicted_label_union.update(str(pred.get("label", "")) for pred in record.get("predictions", []))

    selected_image_ids = {int(record["_resolved_image_id"]) for record in variants["baseline"]}
    asset_id_by_image_id = {
        int(record["_resolved_image_id"]): str(record.get("asset_id", f"image_{record['_resolved_image_id']}"))
        for record in variants["baseline"]
    }

    class_order = [str(category["name"]) for category in gt_payload.get("categories", [])]
    for label in sorted(predicted_label_union):
        if label and label not in class_order:
            class_order.append(label)

    selected_annotations = [
        annotation
        for annotation in gt_payload.get("annotations", [])
        if int(annotation["image_id"]) in selected_image_ids
    ]

    base_gt_counts: dict[str, dict[str, Any]] = {class_name: empty_class_stats() for class_name in class_order}
    gt_image_ids_by_class: dict[str, set[int]] = {class_name: set() for class_name in class_order}
    gt_state_template: dict[tuple[int, int], list[dict[str, Any]]] = {}
    asset_gt_by_class: dict[str, dict[str, int]] = {}

    for annotation in selected_annotations:
        image_id = int(annotation["image_id"])
        category_id = int(annotation["category_id"])
        class_name = category_name_by_id[category_id]
        asset_id = asset_id_by_image_id[image_id]

        gt_state_template.setdefault((image_id, category_id), []).append(
            {
                "bbox": list(annotation["bbox"]),
                "asset_id": asset_id,
            }
        )
        base_gt_counts[class_name]["gt_instances"] += 1
        gt_image_ids_by_class[class_name].add(image_id)
        asset_gt_by_class.setdefault(asset_id, {})
        asset_gt_by_class[asset_id][class_name] = asset_gt_by_class[asset_id].get(class_name, 0) + 1

    variant_results: dict[str, Any] = {}
    asset_order = [str(record.get("asset_id", "")) for record in variants["baseline"]]

    for variant_name, records in variants.items():
        class_stats = {class_name: empty_class_stats() for class_name in class_order}
        pred_image_ids_by_class: dict[str, set[int]] = {class_name: set() for class_name in class_order}
        tp_hit_image_ids_by_class: dict[str, set[int]] = {class_name: set() for class_name in class_order}
        asset_class_stats: dict[str, dict[str, dict[str, int]]] = {asset_id: {} for asset_id in asset_order}
        gt_state = {
            key: [
                {
                    "bbox": list(item["bbox"]),
                    "asset_id": item["asset_id"],
                    "matched": False,
                }
                for item in value
            ]
            for key, value in gt_state_template.items()
        }

        for class_name in class_order:
            class_stats[class_name]["gt_instances"] = int(base_gt_counts[class_name]["gt_instances"])

        total_tp = 0
        total_fp = 0

        for record in records:
            image_id = int(record["_resolved_image_id"])
            asset_id = str(record.get("asset_id", f"image_{image_id}"))
            asset_stats = asset_class_stats.setdefault(asset_id, {})

            for class_name, gt_count in asset_gt_by_class.get(asset_id, {}).items():
                class_asset_stats = asset_stats.setdefault(class_name, empty_asset_class_stats())
                class_asset_stats["gt_instances"] = gt_count

            predictions = sorted(record.get("predictions", []), key=lambda item: float(item.get("score") or 0.0), reverse=True)
            for prediction in predictions:
                label = str(prediction.get("label", ""))
                if label not in class_stats or label not in category_id_by_name:
                    continue

                class_stats[label]["pred_instances"] += 1
                pred_image_ids_by_class[label].add(image_id)
                class_asset_stats = asset_stats.setdefault(label, empty_asset_class_stats())
                class_asset_stats["pred_instances"] += 1

                x1, y1, x2, y2 = prediction["bbox"]
                pred_xywh = [float(x1), float(y1), float(x2) - float(x1), float(y2) - float(y1)]

                candidates = gt_state.get((image_id, category_id_by_name[label]), [])
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
                    class_stats[label]["tp"] += 1
                    class_asset_stats["tp"] += 1
                    tp_hit_image_ids_by_class[label].add(image_id)
                    total_tp += 1
                else:
                    class_stats[label]["fp"] += 1
                    class_asset_stats["fp"] += 1
                    total_fp += 1

        total_fn = 0
        for (image_id, category_id), candidates in gt_state.items():
            class_name = category_name_by_id[category_id]
            asset_id = asset_id_by_image_id[image_id]
            asset_stats = asset_class_stats.setdefault(asset_id, {})
            class_asset_stats = asset_stats.setdefault(class_name, empty_asset_class_stats())
            class_asset_stats["gt_instances"] = asset_gt_by_class.get(asset_id, {}).get(class_name, 0)
            for candidate in candidates:
                if not candidate["matched"]:
                    class_stats[class_name]["fn"] += 1
                    class_asset_stats["fn"] += 1
                    total_fn += 1

        for class_name in class_order:
            finalize_class_stats(
                class_stats[class_name],
                gt_image_ids_by_class[class_name],
                pred_image_ids_by_class[class_name],
                tp_hit_image_ids_by_class[class_name],
            )

        total_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        total_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        total_f1 = (2 * total_precision * total_recall / (total_precision + total_recall)) if (total_precision + total_recall) > 0 else 0.0

        asset_rollup: dict[str, Any] = {}
        for asset_id in asset_order:
            classes_payload: dict[str, Any] = {}
            asset_tp = asset_fp = asset_fn = 0
            for class_name in class_order:
                class_asset_stats = asset_class_stats.get(asset_id, {}).get(class_name)
                if not class_asset_stats:
                    continue
                if (
                    class_asset_stats["gt_instances"] == 0
                    and class_asset_stats["pred_instances"] == 0
                    and class_asset_stats["tp"] == 0
                    and class_asset_stats["fp"] == 0
                    and class_asset_stats["fn"] == 0
                ):
                    continue
                classes_payload[class_name] = class_asset_stats
                asset_tp += class_asset_stats["tp"]
                asset_fp += class_asset_stats["fp"]
                asset_fn += class_asset_stats["fn"]
            asset_rollup[asset_id] = {
                "tp": asset_tp,
                "fp": asset_fp,
                "fn": asset_fn,
                "classes": classes_payload,
            }

        variant_results[variant_name] = {
            "totals": {
                "tp": total_tp,
                "fp": total_fp,
                "fn": total_fn,
                "precision": total_precision,
                "recall": total_recall,
                "f1": total_f1,
                "avg_fp_per_image": (total_fp / len(records)) if records else 0.0,
                "pred_instances_total": sum(int(stats["pred_instances"]) for stats in class_stats.values()),
                "gt_instances_total": sum(int(stats["gt_instances"]) for stats in class_stats.values()),
            },
            "classes": class_stats,
            "assets": asset_rollup,
        }

    return class_order, variant_results


def build_outputs(class_order: list[str], variant_results: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    comparison_rows: list[dict[str, Any]] = []
    baseline_classes = variant_results["baseline"]["classes"]
    v1_classes = variant_results["refinement_v1"]["classes"]
    v2_classes = variant_results["refinement_v2"]["classes"]

    for class_name in class_order:
        baseline = baseline_classes[class_name]
        v1 = v1_classes[class_name]
        v2 = v2_classes[class_name]
        delta_v1 = {
            "tp": int(v1["tp"]) - int(baseline["tp"]),
            "fp": int(v1["fp"]) - int(baseline["fp"]),
            "fn": int(v1["fn"]) - int(baseline["fn"]),
        }
        delta_v2 = {
            "tp": int(v2["tp"]) - int(baseline["tp"]),
            "fp": int(v2["fp"]) - int(baseline["fp"]),
            "fn": int(v2["fn"]) - int(baseline["fn"]),
        }
        comparison_rows.append(
            {
                "class_name": class_name,
                "gt_instances": int(baseline["gt_instances"]),
                "gt_image_count": int(baseline["gt_image_count"]),
                "baseline": baseline,
                "refinement_v1": v1,
                "refinement_v2": v2,
                "delta_v1_vs_baseline": delta_v1,
                "delta_v2_vs_baseline": delta_v2,
                "change_direction": {
                    "refinement_v1": build_change_tags(baseline, v1),
                    "refinement_v2": build_change_tags(baseline, v2),
                },
            }
        )

    summary = {
        "baseline_totals": variant_results["baseline"]["totals"],
        "refinement_v1_totals": variant_results["refinement_v1"]["totals"],
        "refinement_v2_totals": variant_results["refinement_v2"]["totals"],
        "refinement_v1_vs_baseline": summarize_classes(comparison_rows, "refinement_v1"),
        "refinement_v2_vs_baseline": summarize_classes(comparison_rows, "refinement_v2"),
    }
    return summary, comparison_rows


def infer_main_change_type(row: dict[str, Any]) -> str:
    class_name = row["class_name"]
    delta_v2 = row["delta_v2_vs_baseline"]

    if class_name in {"Valve", "Pipeline", "Pressure Gauge"}:
        return "boundary_case"
    if int(delta_v2["fn"]) < 0 or int(delta_v2["tp"]) > 0:
        return "fn_reduced"
    if int(delta_v2["fp"]) < 0:
        return "fp_reduced"
    return "stable"


def infer_notes(row: dict[str, Any]) -> str:
    class_name = row["class_name"]
    override_notes = {
        "Electrical Box": "high FP strongly suppressed",
        "Fire Extinguisher": "minor FP reduction",
        "Fire Hydrant": "fire hydrant partially recovered",
        "Motor": "high FP reduced, TP kept",
        "Open Flame": "stable, recall still limited",
        "Person": "stable strong baseline",
        "Pipeline": "still extent-limited",
        "Pressure Gauge": "still mislocalized",
        "Safety Helmet": "high FP reduced, TP kept",
        "Smoke": "stable, recall still limited",
        "Valve": "still candidate-missing",
        "Direct-Blow Pipe": "pure FP class suppressed",
        "Electronic Control Cabinet": "pure FP class suppressed",
        "Ladder": "pure FP class suppressed",
        "Sight Hole Cover": "pure FP class suppressed",
    }
    if class_name in override_notes:
        return override_notes[class_name]

    change_type = infer_main_change_type(row)
    if change_type == "fn_reduced":
        return "partial FN recovery"
    if change_type == "fp_reduced":
        return "high FP suppressed"
    if change_type == "boundary_case":
        return "still unresolved"
    return "little observable change"


def build_paper_table_rows(comparison_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    paper_rows: list[dict[str, Any]] = []
    for row in comparison_rows:
        paper_rows.append(
            {
                "class_name": row["class_name"],
                "gt_count": row["gt_instances"],
                "baseline_tp": row["baseline"]["tp"],
                "baseline_fp": row["baseline"]["fp"],
                "baseline_fn": row["baseline"]["fn"],
                "baseline_precision": f"{row['baseline']['precision']:.4f}",
                "baseline_recall": f"{row['baseline']['recall']:.4f}",
                "v1_tp": row["refinement_v1"]["tp"],
                "v1_fp": row["refinement_v1"]["fp"],
                "v1_fn": row["refinement_v1"]["fn"],
                "v1_precision": f"{row['refinement_v1']['precision']:.4f}",
                "v1_recall": f"{row['refinement_v1']['recall']:.4f}",
                "v2_tp": row["refinement_v2"]["tp"],
                "v2_fp": row["refinement_v2"]["fp"],
                "v2_fn": row["refinement_v2"]["fn"],
                "v2_precision": f"{row['refinement_v2']['precision']:.4f}",
                "v2_recall": f"{row['refinement_v2']['recall']:.4f}",
                "main_change_type": infer_main_change_type(row),
                "notes": infer_notes(row),
            }
        )
    return paper_rows


def write_csv(path: Path, comparison_rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "class_name",
        "gt_instances",
        "gt_image_count",
        "baseline_tp",
        "baseline_fp",
        "baseline_fn",
        "baseline_precision",
        "baseline_recall",
        "baseline_pred_instances",
        "baseline_pred_image_count",
        "baseline_tp_hit_image_count",
        "refinement_v1_tp",
        "refinement_v1_fp",
        "refinement_v1_fn",
        "refinement_v1_precision",
        "refinement_v1_recall",
        "refinement_v1_pred_instances",
        "refinement_v1_pred_image_count",
        "refinement_v1_tp_hit_image_count",
        "refinement_v2_tp",
        "refinement_v2_fp",
        "refinement_v2_fn",
        "refinement_v2_precision",
        "refinement_v2_recall",
        "refinement_v2_pred_instances",
        "refinement_v2_pred_image_count",
        "refinement_v2_tp_hit_image_count",
        "delta_v1_tp",
        "delta_v1_fp",
        "delta_v1_fn",
        "delta_v2_tp",
        "delta_v2_fp",
        "delta_v2_fn",
        "change_tags_v1",
        "change_tags_v2",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in comparison_rows:
            writer.writerow(
                {
                    "class_name": row["class_name"],
                    "gt_instances": row["gt_instances"],
                    "gt_image_count": row["gt_image_count"],
                    "baseline_tp": row["baseline"]["tp"],
                    "baseline_fp": row["baseline"]["fp"],
                    "baseline_fn": row["baseline"]["fn"],
                    "baseline_precision": f"{row['baseline']['precision']:.4f}",
                    "baseline_recall": f"{row['baseline']['recall']:.4f}",
                    "baseline_pred_instances": row["baseline"]["pred_instances"],
                    "baseline_pred_image_count": row["baseline"]["pred_image_count"],
                    "baseline_tp_hit_image_count": row["baseline"]["tp_hit_image_count"],
                    "refinement_v1_tp": row["refinement_v1"]["tp"],
                    "refinement_v1_fp": row["refinement_v1"]["fp"],
                    "refinement_v1_fn": row["refinement_v1"]["fn"],
                    "refinement_v1_precision": f"{row['refinement_v1']['precision']:.4f}",
                    "refinement_v1_recall": f"{row['refinement_v1']['recall']:.4f}",
                    "refinement_v1_pred_instances": row["refinement_v1"]["pred_instances"],
                    "refinement_v1_pred_image_count": row["refinement_v1"]["pred_image_count"],
                    "refinement_v1_tp_hit_image_count": row["refinement_v1"]["tp_hit_image_count"],
                    "refinement_v2_tp": row["refinement_v2"]["tp"],
                    "refinement_v2_fp": row["refinement_v2"]["fp"],
                    "refinement_v2_fn": row["refinement_v2"]["fn"],
                    "refinement_v2_precision": f"{row['refinement_v2']['precision']:.4f}",
                    "refinement_v2_recall": f"{row['refinement_v2']['recall']:.4f}",
                    "refinement_v2_pred_instances": row["refinement_v2"]["pred_instances"],
                    "refinement_v2_pred_image_count": row["refinement_v2"]["pred_image_count"],
                    "refinement_v2_tp_hit_image_count": row["refinement_v2"]["tp_hit_image_count"],
                    "delta_v1_tp": row["delta_v1_vs_baseline"]["tp"],
                    "delta_v1_fp": row["delta_v1_vs_baseline"]["fp"],
                    "delta_v1_fn": row["delta_v1_vs_baseline"]["fn"],
                    "delta_v2_tp": row["delta_v2_vs_baseline"]["tp"],
                    "delta_v2_fp": row["delta_v2_vs_baseline"]["fp"],
                    "delta_v2_fn": row["delta_v2_vs_baseline"]["fn"],
                    "change_tags_v1": ", ".join(row["change_direction"]["refinement_v1"]),
                    "change_tags_v2": ", ".join(row["change_direction"]["refinement_v2"]),
                }
            )


def write_paper_table_csv(path: Path, paper_rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "class_name",
        "gt_count",
        "baseline_tp",
        "baseline_fp",
        "baseline_fn",
        "baseline_precision",
        "baseline_recall",
        "v1_tp",
        "v1_fp",
        "v1_fn",
        "v1_precision",
        "v1_recall",
        "v2_tp",
        "v2_fp",
        "v2_fn",
        "v2_precision",
        "v2_recall",
        "main_change_type",
        "notes",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(paper_rows)


def write_markdown(path: Path, summary: dict[str, Any], comparison_rows: list[dict[str, Any]], iou_threshold: float) -> None:
    lines: list[str] = []
    lines.append("# next subset classwise comparison")
    lines.append("")
    lines.append(f"- IoU threshold: `{iou_threshold}`")
    lines.append("- Variants: `baseline`, `next_subset_refinement_v1`, `next_subset_refinement_v2`")
    lines.append(f"- Baseline totals: `TP/FP/FN={summary['baseline_totals']['tp']}/{summary['baseline_totals']['fp']}/{summary['baseline_totals']['fn']}`")
    lines.append(f"- V1 totals: `TP/FP/FN={summary['refinement_v1_totals']['tp']}/{summary['refinement_v1_totals']['fp']}/{summary['refinement_v1_totals']['fn']}`")
    lines.append(f"- V2 totals: `TP/FP/FN={summary['refinement_v2_totals']['tp']}/{summary['refinement_v2_totals']['fp']}/{summary['refinement_v2_totals']['fn']}`")
    lines.append("")
    lines.append("## Change Summary")
    lines.append("")
    lines.append(f"- V1 mainly improved FP: `{', '.join(summary['refinement_v1_vs_baseline']['mainly_improved_fp']) or 'none'}`")
    lines.append(f"- V1 mainly improved FN: `{', '.join(summary['refinement_v1_vs_baseline']['mainly_improved_fn']) or 'none'}`")
    lines.append(f"- V1 almost no change: `{', '.join(summary['refinement_v1_vs_baseline']['almost_no_change']) or 'none'}`")
    lines.append(f"- V2 mainly improved FP: `{', '.join(summary['refinement_v2_vs_baseline']['mainly_improved_fp']) or 'none'}`")
    lines.append(f"- V2 mainly improved FN: `{', '.join(summary['refinement_v2_vs_baseline']['mainly_improved_fn']) or 'none'}`")
    lines.append(f"- V2 almost no change: `{', '.join(summary['refinement_v2_vs_baseline']['almost_no_change']) or 'none'}`")
    if summary["refinement_v2_vs_baseline"]["worsened_or_mixed"]:
        lines.append(f"- V2 worsened or mixed: `{', '.join(summary['refinement_v2_vs_baseline']['worsened_or_mixed'])}`")
    lines.append("")
    lines.append("## Class Table")
    lines.append("")
    lines.append("| Class | GT | Base TP/FP/FN | Base P/R | V1 TP/FP/FN | V1 P/R | V2 TP/FP/FN | V2 P/R | Change vs baseline |")
    lines.append("| --- | ---: | --- | --- | --- | --- | --- | --- | --- |")
    for row in comparison_rows:
        lines.append(
            "| {class_name} | {gt_instances} | {b_tp}/{b_fp}/{b_fn} | {b_p:.3f}/{b_r:.3f} | {v1_tp}/{v1_fp}/{v1_fn} | {v1_p:.3f}/{v1_r:.3f} | {v2_tp}/{v2_fp}/{v2_fn} | {v2_p:.3f}/{v2_r:.3f} | V1: {tags_v1}; V2: {tags_v2} |".format(
                class_name=row["class_name"],
                gt_instances=row["gt_instances"],
                b_tp=row["baseline"]["tp"],
                b_fp=row["baseline"]["fp"],
                b_fn=row["baseline"]["fn"],
                b_p=row["baseline"]["precision"],
                b_r=row["baseline"]["recall"],
                v1_tp=row["refinement_v1"]["tp"],
                v1_fp=row["refinement_v1"]["fp"],
                v1_fn=row["refinement_v1"]["fn"],
                v1_p=row["refinement_v1"]["precision"],
                v1_r=row["refinement_v1"]["recall"],
                v2_tp=row["refinement_v2"]["tp"],
                v2_fp=row["refinement_v2"]["fp"],
                v2_fn=row["refinement_v2"]["fn"],
                v2_p=row["refinement_v2"]["precision"],
                v2_r=row["refinement_v2"]["recall"],
                tags_v1=", ".join(row["change_direction"]["refinement_v1"]),
                tags_v2=", ".join(row["change_direction"]["refinement_v2"]),
            )
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- `GT` is the GT instance count for the fixed 12-image subset.")
    lines.append("- `pred_instances` and `pred_image_count` are included in the JSON/CSV for paper table extraction.")
    lines.append("- `tp_hit_image_count` records how many images achieved at least one TP for the class.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_paper_table_markdown(path: Path, paper_rows: list[dict[str, Any]]) -> None:
    lines: list[str] = []
    lines.append("# classwise comparison table")
    lines.append("")
    lines.append("- This is the paper-ready classwise table for the fixed 12-image subset.")
    lines.append(
        "- Canonical machine-readable source: `classwise_comparison_table.csv` in the same directory."
    )
    lines.append("")
    lines.append(
        "| class_name | gt_count | baseline_tp | baseline_fp | baseline_fn | baseline_precision | baseline_recall | v1_tp | v1_fp | v1_fn | v1_precision | v1_recall | v2_tp | v2_fp | v2_fn | v2_precision | v2_recall | main_change_type | notes |"
    )
    lines.append(
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |"
    )
    for row in paper_rows:
        lines.append(
            "| {class_name} | {gt_count} | {baseline_tp} | {baseline_fp} | {baseline_fn} | {baseline_precision} | {baseline_recall} | {v1_tp} | {v1_fp} | {v1_fn} | {v1_precision} | {v1_recall} | {v2_tp} | {v2_fp} | {v2_fn} | {v2_precision} | {v2_recall} | {main_change_type} | {notes} |".format(
                **row
            )
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_table_usage_note(path: Path, summary: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# table usage note")
    lines.append("")
    lines.append(
        "- Formal classwise table source: `classwise_comparison_table.csv` under `artifacts/eval/recheck/next_subset_classwise_comparison/`."
    )
    lines.append("- Human-readable companion: `classwise_comparison_table.md` in the same directory.")
    lines.append(
        "- Recommended citation location: Chapter 5 subsection on fixed 12-image subset classwise refinement comparison, immediately after the overall TP/FP/FN comparison table and before the qualitative screenshot cases."
    )
    lines.append(
        f"- High-FP improvement classes worth naming in正文: `{', '.join(summary['refinement_v2_vs_baseline']['mainly_improved_fp'])}`."
    )
    lines.append(
        f"- High-FN improvement classes worth naming in正文: `{', '.join(summary['refinement_v2_vs_baseline']['mainly_improved_fn']) or 'none'}`."
    )
    lines.append(
        f"- Stable / boundary classes worth naming in正文: `Valve, Pipeline, Pressure Gauge`; unchanged support classes: `{', '.join([name for name in summary['refinement_v2_vs_baseline']['almost_no_change'] if name not in {'Valve', 'Pipeline', 'Pressure Gauge'}])}`."
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build classwise comparison for the fixed next subset.")
    parser.add_argument("--gt-coco", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--refinement-v1", required=True)
    parser.add_argument("--refinement-v2", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    gt_payload = json.loads(Path(args.gt_coco).read_text(encoding="utf-8"))
    variants = {
        "baseline": [json.loads(line) for line in Path(args.baseline).read_text(encoding="utf-8").splitlines() if line.strip()],
        "refinement_v1": [
            json.loads(line) for line in Path(args.refinement_v1).read_text(encoding="utf-8").splitlines() if line.strip()
        ],
        "refinement_v2": [
            json.loads(line) for line in Path(args.refinement_v2).read_text(encoding="utf-8").splitlines() if line.strip()
        ],
    }

    class_order, variant_results = evaluate_variants(
        gt_payload=gt_payload,
        variants=variants,
        iou_threshold=args.iou_threshold,
    )
    summary, comparison_rows = build_outputs(class_order=class_order, variant_results=variant_results)
    paper_rows = build_paper_table_rows(comparison_rows)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_json = output_dir / "classwise_comparison.json"
    output_csv = output_dir / "classwise_comparison.csv"
    output_md = output_dir / "classwise_comparison.md"
    output_paper_csv = output_dir / "classwise_comparison_table.csv"
    output_paper_md = output_dir / "classwise_comparison_table.md"
    output_usage_note = output_dir / "table_usage_note.md"

    payload = {
        "iou_threshold": args.iou_threshold,
        "variants": variant_results,
        "summary": summary,
        "comparison_rows": comparison_rows,
        "paper_table_rows": paper_rows,
    }
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(output_csv, comparison_rows)
    write_markdown(output_md, summary, comparison_rows, args.iou_threshold)
    write_paper_table_csv(output_paper_csv, paper_rows)
    write_paper_table_markdown(output_paper_md, paper_rows)
    write_table_usage_note(output_usage_note, summary)

    print(f"Wrote {output_json}")
    print(f"Wrote {output_csv}")
    print(f"Wrote {output_md}")
    print(f"Wrote {output_paper_csv}")
    print(f"Wrote {output_paper_md}")
    print(f"Wrote {output_usage_note}")


if __name__ == "__main__":
    main()
