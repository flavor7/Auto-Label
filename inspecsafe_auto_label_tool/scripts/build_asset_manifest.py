import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from inspecsafe_auto_label.indexing import build_asset_manifest, summarize_asset_manifest, write_json, write_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the canonical asset manifest for InspecSafe.")
    parser.add_argument("--dataset-root", required=True, help="Path to InspecSafe DATA_PATH directory.")
    parser.add_argument(
        "--output",
        default="artifacts/index/asset_manifest.jsonl",
        help="Output asset manifest JSONL path.",
    )
    parser.add_argument(
        "--summary-output",
        default="artifacts/reports/index_summary.json",
        help="Output summary JSON path.",
    )
    args = parser.parse_args()

    asset_records = build_asset_manifest(args.dataset_root)
    write_jsonl(asset_records, args.output)
    write_json(summarize_asset_manifest(asset_records), args.summary_output)

    print(f"Built asset manifest with {len(asset_records)} assets")
    print(f"Manifest: {Path(args.output).resolve()}")
    print(f"Summary: {Path(args.summary_output).resolve()}")


if __name__ == "__main__":
    main()
