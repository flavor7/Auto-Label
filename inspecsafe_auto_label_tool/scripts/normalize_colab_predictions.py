import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from inspecsafe_auto_label.indexing import load_jsonl, write_jsonl


def normalize_label_name(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


def load_label_mapping(label_schema_path: str | Path) -> dict[str, str]:
    payload = json.loads(Path(label_schema_path).read_text(encoding="utf-8"))
    mapping: dict[str, str] = {}

    for item in payload.get("labels", []):
        canonical_name = item["name"]
        candidates = [canonical_name, *item.get("prompts", [])]
        for candidate in candidates:
            mapping[normalize_label_name(candidate)] = canonical_name

    return mapping


def build_asset_lookup(asset_manifest_path: str | Path) -> tuple[dict[str, dict], dict[str, dict]]:
    records = load_jsonl(asset_manifest_path)
    by_asset_id: dict[str, dict] = {}
    by_sample_id: dict[str, dict] = {}

    for record in records:
        by_asset_id[record["asset_id"]] = record
        sample_id = record["sample_id"]
        if sample_id in by_sample_id:
            raise ValueError(f"Duplicate sample_id in asset manifest: {sample_id}")
        by_sample_id[sample_id] = record

    return by_asset_id, by_sample_id


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize Colab prediction JSONL into the local canonical prediction schema."
    )
    parser.add_argument("--input", required=True, help="Colab prediction JSONL path.")
    parser.add_argument("--asset-manifest", required=True, help="Canonical asset manifest JSONL path.")
    parser.add_argument("--output", required=True, help="Output normalized prediction JSONL path.")
    parser.add_argument(
        "--label-schema",
        default="configs/label_schema.json",
        help="Label schema JSON used to map prompt labels to canonical names.",
    )
    parser.add_argument(
        "--allow-unknown-labels",
        action="store_true",
        help="Keep labels that do not exist in the schema instead of failing.",
    )
    args = parser.parse_args()

    label_mapping = load_label_mapping(args.label_schema)
    assets_by_id, assets_by_sample_id = build_asset_lookup(args.asset_manifest)
    input_records = load_jsonl(args.input)

    normalized_records: list[dict] = []

    for index, record in enumerate(input_records, start=1):
        asset = None
        asset_id = record.get("asset_id")
        if asset_id:
            asset = assets_by_id.get(asset_id)

        image_path = record.get("image_path", "")
        sample_id = record.get("sample_id") or Path(image_path).stem
        if asset is None:
            asset = assets_by_sample_id.get(sample_id)

        if asset is None:
            raise KeyError(
                f"Could not resolve asset for record {index}: asset_id={asset_id!r}, sample_id={sample_id!r}"
            )

        predictions: list[dict] = []
        for prediction in record.get("predictions", []):
            raw_label = prediction["label"]
            canonical_label = label_mapping.get(normalize_label_name(raw_label))
            if canonical_label is None:
                if args.allow_unknown_labels:
                    canonical_label = raw_label
                else:
                    raise KeyError(f"Unknown label {raw_label!r} in record {index}")

            predictions.append(
                {
                    "label": canonical_label,
                    "score": prediction.get("score"),
                    "bbox": prediction.get("bbox", []),
                    "polygon": prediction.get("polygon", []),
                }
            )

        normalized_records.append(
            {
                "asset_id": asset["asset_id"],
                "image_path": asset["image_abs_path"],
                "image_rel_path": asset["image_rel_path"],
                "width": record.get("width", asset["width"]),
                "height": record.get("height", asset["height"]),
                "predictions": predictions,
            }
        )

    write_jsonl(normalized_records, args.output)
    print(f"Normalized {len(normalized_records)} prediction records")
    print(f"Output: {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
