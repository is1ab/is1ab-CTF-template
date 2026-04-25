#!/usr/bin/env python3
"""CLI: 移除 challenges 中冗餘的 reviewer / validation_status / internal_validation_notes 欄位。

Usage:
    uv run python scripts/cleanup-validation-fields.py --dry-run
    uv run python scripts/cleanup-validation-fields.py --apply
    uv run python scripts/cleanup-validation-fields.py --apply --root path/to/challenges
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 讓 setup_helpers 可被 import
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from setup_helpers import cleanup_legacy_validation_fields  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="只預覽，不寫檔")
    mode.add_argument("--apply", action="store_true", help="實際寫檔")
    parser.add_argument(
        "--root",
        default=str(SCRIPT_DIR.parent / "challenges"),
        help="challenges 目錄路徑（預設 ./challenges）",
    )
    args = parser.parse_args()

    challenges_root = Path(args.root).resolve()
    if not challenges_root.exists():
        print(f"❌ challenges 目錄不存在: {challenges_root}")
        return 1

    report = cleanup_legacy_validation_fields(
        challenges_root,
        dry_run=args.dry_run,
    )

    label = "DRY RUN" if report.dry_run else "APPLIED"
    print(f"=== {label} ===")
    print(f"掃描根目錄: {challenges_root}")
    print(f"受影響檔案: {len(report.files_changed)}")
    for path in report.files_changed:
        keys = ", ".join(report.keys_removed.get(path, []))
        rel = path.relative_to(challenges_root)
        print(f"  {rel}  →  移除 {keys}")
    if report.dry_run and report.files_changed:
        print("\n💡 確認無誤後請改用 --apply 實際寫檔。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
