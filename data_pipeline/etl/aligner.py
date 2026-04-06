from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_MIN_TOKENS = 5
DEFAULT_MAX_TOKENS = 100
DEFAULT_MIN_CHAR_LEN = 10
DEFAULT_MAX_LENGTH_RATIO = 3.0


def normalize_text(text: str) -> str:
    """Chuẩn hóa khoảng trắng và xuống dòng."""
    text = str(text or "")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def token_count(text: str) -> int:
    return len(TOKEN_RE.findall(text))


def load_json_records(path: str | Path, text_key: str = "sentence") -> list[dict[str, Any]]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"File {path} phải là JSON array.")

    records: list[dict[str, Any]] = []
    for i, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            continue
        rec_id = item.get("id", i)
        sentence = normalize_text(item.get(text_key, ""))
        records.append({"id": rec_id, "sentence": sentence})
    return records


def build_id_map(records: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in records:
        rec_id = str(item.get("id", "")).strip()
        sent = normalize_text(item.get("sentence", ""))
        if rec_id and sent:
            result[rec_id] = sent
    return result


def is_valid_pair(
    en_text: str,
    vi_text: str,
    min_tokens: int,
    max_tokens: int,
    min_char_len: int,
    max_length_ratio: float,
) -> tuple[bool, str]:
    en_text = normalize_text(en_text)
    vi_text = normalize_text(vi_text)

    if not en_text or not vi_text:
        return False, "empty"

    if len(en_text) < min_char_len or len(vi_text) < min_char_len:
        return False, "too_short_chars"

    en_tokens = token_count(en_text)
    vi_tokens = token_count(vi_text)

    if en_tokens < min_tokens or vi_tokens < min_tokens:
        return False, "too_short_tokens"

    if en_tokens > max_tokens or vi_tokens > max_tokens:
        return False, "too_long_tokens"

    shorter = max(1, min(en_tokens, vi_tokens))
    longer = max(en_tokens, vi_tokens)
    ratio = longer / shorter
    if ratio > max_length_ratio:
        return False, "length_ratio"

    return True, "ok"


def align_records(
    en_records: list[dict[str, Any]],
    vi_records: list[dict[str, Any]],
    min_tokens: int,
    max_tokens: int,
    min_char_len: int,
    max_length_ratio: float,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    en_map = build_id_map(en_records)
    vi_map = build_id_map(vi_records)

    shared_ids = sorted(set(en_map.keys()) & set(vi_map.keys()), key=lambda x: int(x) if x.isdigit() else x)

    stats = {
        "total_en": len(en_records),
        "total_vi": len(vi_records),
        "shared_ids": len(shared_ids),
        "kept": 0,
        "dropped_empty": 0,
        "dropped_too_short_chars": 0,
        "dropped_too_short_tokens": 0,
        "dropped_too_long_tokens": 0,
        "dropped_length_ratio": 0,
    }

    aligned: list[dict[str, Any]] = []
    for rec_id in shared_ids:
        en_text = en_map[rec_id]
        vi_text = vi_map[rec_id]
        ok, reason = is_valid_pair(
            en_text,
            vi_text,
            min_tokens=min_tokens,
            max_tokens=max_tokens,
            min_char_len=min_char_len,
            max_length_ratio=max_length_ratio,
        )
        if not ok:
            if reason == "empty":
                stats["dropped_empty"] += 1
            elif reason == "too_short_chars":
                stats["dropped_too_short_chars"] += 1
            elif reason == "too_short_tokens":
                stats["dropped_too_short_tokens"] += 1
            elif reason == "too_long_tokens":
                stats["dropped_too_long_tokens"] += 1
            elif reason == "length_ratio":
                stats["dropped_length_ratio"] += 1
            continue

        aligned.append({
            "id": int(rec_id) if rec_id.isdigit() else rec_id,
            "en": en_text,
            "vi": vi_text,
        })
        stats["kept"] += 1

    return aligned, stats



def save_tsv(records: list[dict[str, Any]], output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        for item in records:
            writer.writerow([item["en"], item["vi"]])



def save_json(records: list[dict[str, Any]], output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Align cặp câu EN-VI từ 2 file JSON và loại câu quá ngắn/dài."
    )
    parser.add_argument("--en", required=True, help="File JSON tiếng Anh")
    parser.add_argument("--vi", required=True, help="File JSON tiếng Việt")
    parser.add_argument("--output", required=True, help="File output (.tsv hoặc .json)")
    parser.add_argument("--en-key", default="sentence", help="Tên key chứa câu EN")
    parser.add_argument("--vi-key", default="sentence", help="Tên key chứa câu VI")
    parser.add_argument("--min-tokens", type=int, default=DEFAULT_MIN_TOKENS)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--min-char-len", type=int, default=DEFAULT_MIN_CHAR_LEN)
    parser.add_argument("--max-length-ratio", type=float, default=DEFAULT_MAX_LENGTH_RATIO)
    parser.add_argument(
        "--format",
        choices=["auto", "tsv", "json"],
        default="auto",
        help="Định dạng output. auto = suy ra theo đuôi file",
    )
    return parser.parse_args()



def main() -> None:
    args = parse_args()

    en_records = load_json_records(args.en, text_key=args.en_key)
    vi_records = load_json_records(args.vi, text_key=args.vi_key)

    aligned, stats = align_records(
        en_records,
        vi_records,
        min_tokens=args.min_tokens,
        max_tokens=args.max_tokens,
        min_char_len=args.min_char_len,
        max_length_ratio=args.max_length_ratio,
    )

    output_format = args.format
    if output_format == "auto":
        suffix = Path(args.output).suffix.lower()
        output_format = "json" if suffix == ".json" else "tsv"

    if output_format == "json":
        save_json(aligned, args.output)
    else:
        save_tsv(aligned, args.output)

    print("=" * 60)
    print("ALIGN REPORT")
    print(f"EN records      : {stats['total_en']}")
    print(f"VI records      : {stats['total_vi']}")
    print(f"Shared ids      : {stats['shared_ids']}")
    print(f"Kept pairs      : {stats['kept']}")
    print(f"Drop empty      : {stats['dropped_empty']}")
    print(f"Drop short char : {stats['dropped_too_short_chars']}")
    print(f"Drop short tok  : {stats['dropped_too_short_tokens']}")
    print(f"Drop long tok   : {stats['dropped_too_long_tokens']}")
    print(f"Drop len ratio  : {stats['dropped_length_ratio']}")
    print(f"Saved to        : {args.output}")
    print("=" * 60)


if __name__ == "__main__":
    main()
