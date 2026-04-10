import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from inspecsafe_auto_label.exporters import (
    load_jsonl,
    predictions_to_coco,
    predictions_to_label_studio,
    write_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export prediction JSONL to COCO or Label Studio JSON.")
    parser.add_argument("--input", required=True, help="Prediction JSONL path.")
    parser.add_argument("--format", required=True, choices=("coco", "label_studio"))
    parser.add_argument("--output", required=True, help="Output JSON path.")
    parser.add_argument(
        "--asset-manifest",
        default=None,
        help="Optional canonical asset manifest JSONL path used to enrich predictions with asset metadata.",
    )
    parser.add_argument(
        "--document-root",
        default=None,
        help="Optional Label Studio local files document root when exporting label_studio format.",
    )
    parser.add_argument(
        "--url-prefix",
        default=None,
        help="Optional HTTP prefix for Label Studio image URLs, for example http://127.0.0.1:9000 .",
    )
    parser.add_argument(
        "--url-root",
        default=None,
        help="Optional filesystem root used with --url-prefix. Defaults to --document-root.",
    )
    parser.add_argument(
        "--model-version",
        default="unknown",
        help="Model version label attached to Label Studio predictions.",
    )
    args = parser.parse_args()

    records = load_jsonl(args.input)
    asset_records = load_jsonl(args.asset_manifest) if args.asset_manifest else None
    if args.format == "coco":
        payload = predictions_to_coco(records)
    else:
        payload = predictions_to_label_studio(
            records,
            asset_records=asset_records,
            document_root=args.document_root,
            url_prefix=args.url_prefix,
            url_root=args.url_root,
            model_version=args.model_version,
        )
    write_json(payload, args.output)
    print(f"Exported {len(records)} records to {args.output}")


if __name__ == "__main__":
    main()
