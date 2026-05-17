from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path
from typing import Iterable

TOKEN_RE = re.compile(r"\S+")
VI_CHAR_RE = re.compile(r"[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]", re.IGNORECASE)
EN_HINT_RE = re.compile(r"\b(the|and|is|are|of|to|in|for|with|that|this|from|by|on|as|an|be)\b", re.IGNORECASE)
VI_HINT_RE = re.compile(r"\b(và|là|của|cho|trong|được|với|một|những|các|từ|về|trên|như|bởi)\b", re.IGNORECASE)


def token_count(text: str) -> int:
    return len(TOKEN_RE.findall(text or ""))


def detect_lang_heuristic(text: str) -> tuple[str, float]:
    text = (text or "").strip()
    if not text:
        return "unknown", 0.0

    vi_score = 0.0
    en_score = 0.0

    vi_chars = len(VI_CHAR_RE.findall(text))
    if vi_chars > 0:
        vi_score += min(1.0, 0.2 + vi_chars * 0.08)

    vi_hints = len(VI_HINT_RE.findall(text))
    en_hints = len(EN_HINT_RE.findall(text))
    vi_score += min(0.8, vi_hints * 0.08)
    en_score += min(0.8, en_hints * 0.06)

    ascii_ratio = sum(ord(c) < 128 for c in text) / max(1, len(text))
    if ascii_ratio > 0.92:
        en_score += 0.25
    if vi_chars > 0:
        vi_score += 0.15

    if vi_score >= en_score:
        conf = min(0.99, max(0.5, vi_score - en_score + 0.55))
        return "vi", conf

    conf = min(0.99, max(0.5, en_score - vi_score + 0.55))
    return "en", conf


def validate_quality(
    path: Path,
    min_tokens: int = 5,
    max_tokens: int = 100,
    min_confidence: float = 0.90,
) -> tuple[bool, dict]:
    stats = {
        "file": str(path),
        "total_lines": 0,
        "valid_lines": 0,
        "invalid_lines": 0,
        "bad_length": 0,
        "bad_language": 0,
        "errors": [],
    }

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        for line_no, row in enumerate(reader, start=1):
            if len(row) != 2:
                continue

            en, vi = row[0].strip(), row[1].strip()
            stats["total_lines"] += 1

            en_tokens = token_count(en)
            vi_tokens = token_count(vi)

            line_ok = True

            if not (min_tokens <= en_tokens <= max_tokens) or not (min_tokens <= vi_tokens <= max_tokens):
                stats["bad_length"] += 1
                stats["errors"].append(
                    f"Line {line_no}: token_count out of range | en={en_tokens}, vi={vi_tokens}"
                )
                line_ok = False

            en_lang, en_conf = detect_lang_heuristic(en)
            vi_lang, vi_conf = detect_lang_heuristic(vi)

            if en_lang != "en" or en_conf < min_confidence or vi_lang != "vi" or vi_conf < min_confidence:
                stats["bad_language"] += 1
                stats["errors"].append(
                    f"Line {line_no}: language mismatch | en=({en_lang},{en_conf:.2f}) vi=({vi_lang},{vi_conf:.2f})"
                )
                line_ok = False

            if line_ok:
                stats["valid_lines"] += 1
            else:
                stats["invalid_lines"] += 1

    ok = stats["invalid_lines"] == 0
    return ok, stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kiểm tra chất lượng: độ dài câu, language detection.")
    parser.add_argument("--file", required=True, help="Đường dẫn file TSV")
    parser.add_argument("--min-tokens", type=int, default=5, help="Số token tối thiểu")
    parser.add_argument("--max-tokens", type=int, default=100, help="Số token tối đa")
    parser.add_argument("--min-confidence", type=float, default=0.90, help="Ngưỡng confidence ngôn ngữ")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = Path(args.file)

    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {path}")

    ok, stats = validate_quality(
        path=path,
        min_tokens=args.min_tokens,
        max_tokens=args.max_tokens,
        min_confidence=args.min_confidence,
    )

    print("=" * 60)
    print("QUALITY VALIDATOR SUMMARY")
    print("=" * 60)
    print(f"File          : {stats['file']}")
    print(f"Total lines   : {stats['total_lines']}")
    print(f"Valid lines   : {stats['valid_lines']}")
    print(f"Invalid lines : {stats['invalid_lines']}")
    print(f"Bad length    : {stats['bad_length']}")
    print(f"Bad language  : {stats['bad_language']}")

    if stats["errors"]:
        print("-" * 60)
        print("ERRORS (first 20)")
        for err in stats["errors"][:20]:
            print(err)

    print("=" * 60)
    if ok:
        print("[PASS] Quality check hợp lệ")
    else:
        print("[FAIL] Quality check không hợp lệ")


if __name__ == "__main__":
    main()
