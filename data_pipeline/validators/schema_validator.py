from __future__ import annotations

import argparse
import csv
from pathlib import Path


UTF8_BOM = b"\xef\xbb\xbf"


def detect_bom(path: Path) -> bool:
    with path.open("rb") as f:
        start = f.read(3)
    return start == UTF8_BOM


def validate_tsv_schema(path: Path, require_non_empty: bool = True) -> tuple[bool, dict]:
    stats = {
        "file": str(path),
        "bom": False,
        "total_lines": 0,
        "valid_lines": 0,
        "invalid_lines": 0,
        "errors": [],
    }

    try:
        stats["bom"] = detect_bom(path)
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f, delimiter="\t")
            for line_no, row in enumerate(reader, start=1):
                stats["total_lines"] += 1

                if len(row) != 2:
                    stats["invalid_lines"] += 1
                    stats["errors"].append(f"Line {line_no}: expected 2 columns, got {len(row)}")
                    continue

                en, vi = row[0].strip(), row[1].strip()
                if require_non_empty and (not en or not vi):
                    stats["invalid_lines"] += 1
                    stats["errors"].append(f"Line {line_no}: empty EN or VI column")
                    continue

                stats["valid_lines"] += 1

    except UnicodeDecodeError as e:
        stats["errors"].append(f"UTF-8 decode error: {e}")
        return False, stats
    except Exception as e:
        stats["errors"].append(f"Unexpected error: {e}")
        return False, stats

    ok = (not stats["bom"]) and stats["invalid_lines"] == 0 and len(stats["errors"]) == 0
    return ok, stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kiểm tra schema TSV: 2 cột, UTF-8, không BOM.")
    parser.add_argument("--file", required=True, help="Đường dẫn file TSV")
    parser.add_argument("--allow-empty", action="store_true", help="Cho phép cột EN/VI rỗng")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = Path(args.file)

    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {path}")

    ok, stats = validate_tsv_schema(path, require_non_empty=not args.allow_empty)

    print("=" * 60)
    print("SCHEMA VALIDATOR SUMMARY")
    print("=" * 60)
    print(f"File          : {stats['file']}")
    print(f"UTF-8 BOM     : {stats['bom']}")
    print(f"Total lines   : {stats['total_lines']}")
    print(f"Valid lines   : {stats['valid_lines']}")
    print(f"Invalid lines : {stats['invalid_lines']}")

    if stats["errors"]:
        print("-" * 60)
        print("ERRORS (first 20)")
        for err in stats["errors"][:20]:
            print(err)

    print("=" * 60)
    if ok:
        print("[PASS] TSV schema hợp lệ")
    else:
        print("[FAIL] TSV schema không hợp lệ")


if __name__ == "__main__":
    main()
