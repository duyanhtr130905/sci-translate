from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


MULTISPACE_RE = re.compile(r"\s+")


def normalize_text(text: Any, unicode_form: str = "NFKC", lower: bool = False) -> str:
    if text is None:
        return ""
    text = str(text)
    text = unicodedata.normalize(unicode_form, text)
    text = MULTISPACE_RE.sub(" ", text).strip()
    if lower:
        text = text.lower()
    return text


def make_hash_key(values: list[str]) -> str:
    raw = " ||| ".join(values)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_tsv(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        for idx, cols in enumerate(reader, start=1):
            if not cols:
                continue
            if len(cols) >= 2:
                rows.append({"id": idx, "en": cols[0], "vi": cols[1]})
            elif len(cols) == 1:
                rows.append({"id": idx, "sentence": cols[0]})
    return rows


def write_tsv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        for row in rows:
            writer.writerow([row.get(field, "") for field in fields])


def infer_fields(sample: dict[str, Any], mode: str) -> list[str]:
    if mode == "bilingual":
        return ["en", "vi"]
    if mode == "monolingual":
        if "sentence" in sample:
            return ["sentence"]
        if "text" in sample:
            return ["text"]
        return ["sentence"]

    if "en" in sample and "vi" in sample:
        return ["en", "vi"]
    if "sentence" in sample:
        return ["sentence"]
    if "text" in sample:
        return ["text"]
    return ["sentence"]


def deduplicate_rows(
    rows: list[dict[str, Any]],
    fields: list[str],
    unicode_form: str = "NFKC",
    lower: bool = False,
    drop_empty: bool = False,
) -> tuple[list[dict[str, Any]], int, int]:
    seen: set[str] = set()
    kept_rows: list[dict[str, Any]] = []
    dup_count = 0
    empty_count = 0

    for row in rows:
        values = [
            normalize_text(row.get(field, ""), unicode_form=unicode_form, lower=lower)
            for field in fields
        ]

        if drop_empty and any(v == "" for v in values):
            empty_count += 1
            continue

        key = make_hash_key(values)
        if key in seen:
            dup_count += 1
            continue

        seen.add(key)
        kept_rows.append(row)

    return kept_rows, dup_count, empty_count


def process_file(
    input_path: Path,
    output_path: Path,
    mode: str,
    fields: list[str] | None,
    unicode_form: str,
    lower: bool,
    drop_empty: bool,
) -> tuple[int, int, int, int, list[str]]:
    suffix = input_path.suffix.lower()
    if suffix == ".json":
        data = read_json(input_path)
        if not isinstance(data, list):
            raise ValueError("JSON input phải là list các record.")
        rows = [row for row in data if isinstance(row, dict)]
    elif suffix == ".jsonl":
        rows = read_jsonl(input_path)
    elif suffix == ".tsv":
        rows = read_tsv(input_path)
    else:
        raise ValueError("Chỉ hỗ trợ .json, .jsonl, .tsv")

    if not rows:
        raise ValueError("Không có record hợp lệ trong file input.")

    used_fields = fields if fields else infer_fields(rows[0], mode=mode)
    deduped, dup_count, empty_count = deduplicate_rows(
        rows=rows,
        fields=used_fields,
        unicode_form=unicode_form,
        lower=lower,
        drop_empty=drop_empty,
    )

    out_suffix = output_path.suffix.lower()
    if out_suffix == ".json":
        write_json(output_path, deduped)
    elif out_suffix == ".jsonl":
        write_jsonl(output_path, deduped)
    elif out_suffix == ".tsv":
        write_tsv(output_path, deduped, used_fields)
    else:
        raise ValueError("Output chỉ hỗ trợ .json, .jsonl, .tsv")

    return len(rows), len(deduped), dup_count, empty_count, used_fields


def build_output_file(input_file: Path, input_root: Path, output_root: Path, suffix_replacement: tuple[str, str] | None) -> Path:
    relative = input_file.relative_to(input_root)
    out_file = output_root / relative
    if suffix_replacement:
        old, new = suffix_replacement
        if out_file.stem.endswith(old):
            out_file = out_file.with_name(out_file.stem[: -len(old)] + new + out_file.suffix)
        else:
            out_file = out_file.with_name(out_file.stem + new + out_file.suffix)
    return out_file


def process_path(
    input_path: Path,
    output_path: Path,
    mode: str,
    fields: list[str] | None,
    unicode_form: str,
    lower: bool,
    drop_empty: bool,
    rename_suffix_from: str | None,
    rename_suffix_to: str | None,
) -> None:
    supported = {".json", ".jsonl", ".tsv"}
    totals = {
        "files": 0,
        "records": 0,
        "kept": 0,
        "dup": 0,
        "empty": 0,
    }

    if input_path.is_file():
        if not output_path.suffix:
            output_path = output_path / input_path.name
        total, kept, dup, empty, used_fields = process_file(
            input_path=input_path,
            output_path=output_path,
            mode=mode,
            fields=fields,
            unicode_form=unicode_form,
            lower=lower,
            drop_empty=drop_empty,
        )
        print("=" * 60)
        print("DEDUPLICATOR SUMMARY")
        print("=" * 60)
        print(f"Input file       : {input_path}")
        print(f"Output file      : {output_path}")
        print(f"Mode             : {mode}")
        print(f"Fields used      : {used_fields}")
        print(f"Records total    : {total}")
        print(f"Duplicates drop  : {dup}")
        print(f"Empty drop       : {empty}")
        print(f"Records kept     : {kept}")
        print("=" * 60)
        return

    files = sorted([p for p in input_path.rglob("*") if p.is_file() and p.suffix.lower() in supported])
    if not files:
        raise ValueError(f"Không tìm thấy file .json/.jsonl/.tsv trong thư mục: {input_path}")

    output_path.mkdir(parents=True, exist_ok=True)
    suffix_replacement = None
    if rename_suffix_from is not None and rename_suffix_to is not None:
        suffix_replacement = (rename_suffix_from, rename_suffix_to)

    for file_path in files:
        out_file = build_output_file(file_path, input_path, output_path, suffix_replacement)
        total, kept, dup, empty, used_fields = process_file(
            input_path=file_path,
            output_path=out_file,
            mode=mode,
            fields=fields,
            unicode_form=unicode_form,
            lower=lower,
            drop_empty=drop_empty,
        )
        totals["files"] += 1
        totals["records"] += total
        totals["kept"] += kept
        totals["dup"] += dup
        totals["empty"] += empty
        print(
            f"[DONE] {file_path} -> {out_file} | mode={mode} fields={used_fields} "
            f"total={total} kept={kept} dup_drop={dup} empty_drop={empty}"
        )

    print("=" * 60)
    print("DEDUPLICATOR SUMMARY")
    print("=" * 60)
    print(f"Files processed  : {totals['files']}")
    print(f"Records total    : {totals['records']}")
    print(f"Duplicates drop  : {totals['dup']}")
    print(f"Empty drop       : {totals['empty']}")
    print(f"Records kept     : {totals['kept']}")
    print(f"Output folder    : {output_path}")
    print("=" * 60)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Loại trùng lặp bằng hash cho dữ liệu song ngữ hoặc đơn ngữ. Hỗ trợ file hoặc cả thư mục."
    )
    parser.add_argument("--input", required=True, help="File hoặc thư mục đầu vào: .json, .jsonl hoặc .tsv")
    parser.add_argument("--output", required=True, help="File hoặc thư mục đầu ra: .json, .jsonl hoặc .tsv")
    parser.add_argument(
        "--mode",
        default="auto",
        choices=["auto", "bilingual", "monolingual"],
        help="Tự nhận diện hoặc ép kiểu dữ liệu",
    )
    parser.add_argument(
        "--fields",
        nargs="*",
        default=None,
        help="Các field dùng để tạo hash, ví dụ: en vi hoặc sentence",
    )
    parser.add_argument(
        "--unicode-form",
        default="NFKC",
        choices=["NFC", "NFD", "NFKC", "NFKD"],
        help="Kiểu normalize unicode trước khi hash",
    )
    parser.add_argument(
        "--lower",
        action="store_true",
        help="Lowercase trước khi hash để bỏ phân biệt hoa thường",
    )
    parser.add_argument(
        "--drop-empty",
        action="store_true",
        help="Bỏ record nếu một trong các field hash bị rỗng",
    )
    parser.add_argument(
        "--rename-suffix-from",
        default=None,
        help="Nếu input là thư mục, thay hậu tố tên file, ví dụ _aligned",
    )
    parser.add_argument(
        "--rename-suffix-to",
        default=None,
        help="Nếu input là thư mục, đổi sang hậu tố mới, ví dụ _dedup",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Không tìm thấy input: {input_path}")

    process_path(
        input_path=input_path,
        output_path=output_path,
        mode=args.mode,
        fields=args.fields,
        unicode_form=args.unicode_form,
        lower=args.lower,
        drop_empty=args.drop_empty,
        rename_suffix_from=args.rename_suffix_from,
        rename_suffix_to=args.rename_suffix_to,
    )


if __name__ == "__main__":
    main()
