import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from inspecsafe_auto_label.indexing import build_asset_manifest, derive_legacy_image_index, summarize_asset_manifest, write_json, write_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a legacy image index JSONL derived from the canonical asset manifest."
    )
    parser.add_argument("--dataset-root", required=True, help="Path to InspecSafe DATA_PATH directory.")
    parser.add_argument("--output", required=True, help="Output legacy image index JSONL path.")
    parser.add_argument(
        "--summary-output",
        default=None,
        help="Optional summary JSON path. Defaults to <output_dir>/image_index_summary.json.",
    )
    args = parser.parse_args()

    asset_records = build_asset_manifest(args.dataset_root)
    legacy_records = derive_legacy_image_index(asset_records)
    write_jsonl(legacy_records, args.output)

    summary_output = args.summary_output
    if summary_output is None:
        summary_output = str(Path(args.output).with_name("image_index_summary.json"))
    write_json(summarize_asset_manifest(asset_records), summary_output)

    print(f"Indexed {len(legacy_records)} images")
    print(f"JSONL: {Path(args.output).resolve()}")
    print(f"Summary: {Path(summary_output).resolve()}")


if __name__ == "__main__":
    main()
