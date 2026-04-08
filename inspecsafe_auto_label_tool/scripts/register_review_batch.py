import argparse
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from inspecsafe_auto_label.indexing import append_jsonl, load_jsonl
from inspecsafe_auto_label.types import ReviewBatchRecord


def main() -> None:
    parser = argparse.ArgumentParser(description="Register one human review export batch.")
    parser.add_argument("--review-batch-id", required=True, help="Batch id, for example review_20260408_001.")
    parser.add_argument("--review-export-path", required=True, help="Human review export file path.")
    parser.add_argument("--asset-manifest-path", required=True, help="Canonical asset manifest JSONL path.")
    parser.add_argument("--platform", default="label_studio", help="Source annotation platform.")
    parser.add_argument("--based-on-prediction-run-id", default="", help="Optional upstream prediction batch id.")
    parser.add_argument(
        "--output",
        default="artifacts/index/review_manifest.jsonl",
        help="Review manifest JSONL path.",
    )
    parser.add_argument("--notes", default="", help="Optional notes.")
    args = parser.parse_args()

    item_count = len(load_jsonl(args.review_export_path))
    record = ReviewBatchRecord(
        review_batch_id=args.review_batch_id,
        platform=args.platform,
        review_export_path=str(Path(args.review_export_path).resolve()),
        asset_manifest_path=str(Path(args.asset_manifest_path).resolve()),
        item_count=item_count,
        updated_at=datetime.now().isoformat(timespec="seconds"),
        based_on_prediction_run_id=args.based_on_prediction_run_id,
        notes=args.notes,
    )
    append_jsonl([record], args.output)
    print(f"Registered review batch: {args.review_batch_id}")
    print(f"Items: {item_count}")
    print(f"Manifest: {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
