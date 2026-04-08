import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from inspecsafe_auto_label.indexing import load_jsonl, validate_asset_manifest_records, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the canonical asset manifest.")
    parser.add_argument("--input", required=True, help="Asset manifest JSONL path.")
    parser.add_argument(
        "--dataset-root",
        default=None,
        help="Optional DATA_PATH root used to validate image_rel_path reconstruction.",
    )
    parser.add_argument("--verify-sha1", action="store_true", help="Recompute sha1 for all images.")
    parser.add_argument(
        "--report-output",
        default="artifacts/reports/asset_manifest_validation.json",
        help="Validation report JSON path.",
    )
    args = parser.parse_args()

    records = load_jsonl(args.input)
    report = validate_asset_manifest_records(records, dataset_root=args.dataset_root, verify_sha1=args.verify_sha1)
    write_json(report, args.report_output)

    print(f"Validated {report['total_records']} records")
    print(f"Issues: {report['issue_count']}")
    print(f"Report: {Path(args.report_output).resolve()}")
    if report["issue_count"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
