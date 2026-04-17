import json
from pathlib import Path

import cv2


def draw_boxes(image_path: Path, predictions: list[dict], output_path: Path, title: str) -> None:
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    for pred in predictions:
        x1, y1, x2, y2 = [int(v) for v in pred["bbox"]]
        score = float(pred.get("score") or 0.0)
        label = pred["label"]
        cv2.rectangle(image, (x1, y1), (x2, y2), (50, 220, 50), 2)
        cv2.putText(
            image,
            f"{label}:{score:.2f}",
            (x1, max(20, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (50, 220, 50),
            1,
            cv2.LINE_AA,
        )

    cv2.putText(
        image,
        title,
        (12, 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 0),
        2,
        cv2.LINE_AA,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), image)


def main() -> None:
    root = Path('/root/autodl-tmp/inspecsafe/program_git/inspecsafe_auto_label_tool')
    baseline_path = root / 'artifacts/eval/recheck/subset3_predictions.jsonl'
    refined_path = root / 'artifacts/eval/recheck/subset3_refinement/refined_predictions.jsonl'
    out_dir = root / 'artifacts/eval/recheck/subset3_refinement/visual_compare'

    baseline = [json.loads(x) for x in baseline_path.read_text(encoding='utf-8').splitlines() if x.strip()]
    refined = [json.loads(x) for x in refined_path.read_text(encoding='utf-8').splitlines() if x.strip()]
    refined_by_asset = {r['asset_id']: r for r in refined}

    summary_rows: list[dict] = []

    for base in baseline:
        asset_id = base['asset_id']
        ref = refined_by_asset[asset_id]
        image_path = Path(base['image_path'])

        base_preds = base.get('predictions', [])
        ref_preds = ref.get('predictions', [])

        draw_boxes(
            image_path=image_path,
            predictions=base_preds,
            output_path=out_dir / f"{asset_id.replace(':', '_')}_baseline.jpg",
            title=f"BASELINE {asset_id} count={len(base_preds)}",
        )
        draw_boxes(
            image_path=image_path,
            predictions=ref_preds,
            output_path=out_dir / f"{asset_id.replace(':', '_')}_refinement.jpg",
            title=f"REFINEMENT {asset_id} count={len(ref_preds)}",
        )

        summary_rows.append(
            {
                'asset_id': asset_id,
                'baseline_pred_count': len(base_preds),
                'refinement_pred_count': len(ref_preds),
                'removed': len(base_preds) - len(ref_preds),
                'baseline_labels': [p['label'] for p in base_preds],
                'refinement_labels': [p['label'] for p in ref_preds],
            }
        )

    (out_dir / 'compare_summary.json').write_text(
        json.dumps(summary_rows, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print(out_dir)


if __name__ == '__main__':
    main()
