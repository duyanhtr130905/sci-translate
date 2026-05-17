from __future__ import annotations

import argparse
import html
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


HTML_TAG_RE = re.compile(r"<[^>]+>")
MULTISPACE_RE = re.compile(r"\s+")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200D\uFEFF]")

LATEX_CMD_TWO_ARGS_RE = re.compile(
    r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}\{([^{}]*)\}"
)
LATEX_CMD_ONE_ARG_RE = re.compile(
    r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}"
)

DOUBLE_SLASH_RE = re.compile(r"\s*//\s*")


def strip_html(text: str) -> str:
    return HTML_TAG_RE.sub(" ", text)


def normalize_unicode(text: str, form: str = "NFKC") -> str:
    return unicodedata.normalize(form, text)


def has_url_like(text: str) -> bool:
    if text is None:
        return False
    text = str(text).lower()
    url_markers = [
        "https",
        "http",
        "www.",
        "github.com",
        "huggingface.co",
    ]
    return any(marker in text for marker in url_markers)


def record_has_url(record: dict[str, Any], text_fields: list[str]) -> bool:
    for field in text_fields:
        if field in record and has_url_like(record.get(field, "")):
            return True
    return False


def clean_text(text: str, unicode_form: str = "NFKC") -> str:
    if text is None:
        return ""

    text = str(text)

    text = html.unescape(text)

    # \cmd{a}{b} -> giữ lại b
    for _ in range(3):
        text = LATEX_CMD_TWO_ARGS_RE.sub(r"\2", text)

    # \cmd{a} -> giữ lại a
    for _ in range(3):
        text = LATEX_CMD_ONE_ARG_RE.sub(r"\1", text)

    text = strip_html(text)
    text = ZERO_WIDTH_RE.sub("", text)
    text = CONTROL_CHAR_RE.sub(" ", text)
    text = normalize_unicode(text, form=unicode_form)
    text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")

    # bỏ //
    text = DOUBLE_SLASH_RE.sub(" ", text)

    # xóa toàn bộ backslash còn sót lại
    text = text.replace("\\", "")

    # bỏ dấu nháy kép còn sót lại: \" và "
    text = text.replace('\\"', "").replace('"', "")

    text = MULTISPACE_RE.sub(" ", text).strip()
    return text


def clean_record(
    record: dict[str, Any],
    text_fields: list[str],
    unicode_form: str = "NFKC",
) -> dict[str, Any]:
    cleaned = dict(record)

    for field in text_fields:
        if field in cleaned:
            cleaned[field] = clean_text(cleaned[field], unicode_form=unicode_form)

    return cleaned


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                records.append(obj)
    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def process_json_file(
    input_path: Path,
    output_path: Path,
    text_fields: list[str],
    unicode_form: str,
    drop_empty: bool,
    drop_url: bool,
) -> tuple[int, int, int]:
    data = read_json(input_path)

    total = 0
    kept = 0
    dropped_url = 0

    if isinstance(data, list):
        cleaned_items = []

        for item in data:
            if not isinstance(item, dict):
                continue

            total += 1

            # lọc URL trên text gốc trước khi clean
            if drop_url and record_has_url(item, text_fields):
                dropped_url += 1
                continue

            cleaned = clean_record(item, text_fields, unicode_form=unicode_form)

            if drop_empty:
                has_text = any(
                    cleaned.get(field, "")
                    for field in text_fields
                    if field in cleaned
                )
                if not has_text:
                    continue

            cleaned_items.append(cleaned)
            kept += 1

        write_json(output_path, cleaned_items)

    elif isinstance(data, dict):
        total = 1

        if drop_url and record_has_url(data, text_fields):
            dropped_url = 1
            write_json(output_path, {})
            return total, 0, dropped_url

        cleaned = clean_record(data, text_fields, unicode_form=unicode_form)

        if not drop_empty or any(
            cleaned.get(field, "")
            for field in text_fields
            if field in cleaned
        ):
            write_json(output_path, cleaned)
            kept = 1
        else:
            write_json(output_path, {})
            kept = 0

    else:
        write_json(output_path, data)

    return total, kept, dropped_url


def process_jsonl_file(
    input_path: Path,
    output_path: Path,
    text_fields: list[str],
    unicode_form: str,
    drop_empty: bool,
    drop_url: bool,
) -> tuple[int, int, int]:
    records = read_jsonl(input_path)

    cleaned_records = []
    total = 0
    kept = 0
    dropped_url = 0

    for rec in records:
        total += 1

        if drop_url and record_has_url(rec, text_fields):
            dropped_url += 1
            continue

        cleaned = clean_record(rec, text_fields, unicode_form=unicode_form)

        if drop_empty:
            has_text = any(
                cleaned.get(field, "")
                for field in text_fields
                if field in cleaned
            )
            if not has_text:
                continue

        cleaned_records.append(cleaned)
        kept += 1

    write_jsonl(output_path, cleaned_records)
    return total, kept, dropped_url


def infer_default_text_fields() -> list[str]:
    return ["sentence", "abstract", "title", "text", "en", "vi"]


def process_path(
    input_path: Path,
    output_path: Path,
    text_fields: list[str],
    unicode_form: str,
    drop_empty: bool,
    drop_url: bool,
) -> None:
    total_files = 0
    total_records = 0
    kept_records = 0
    dropped_url_records = 0

    if input_path.is_file():
        files = [input_path]
        base_input_dir = input_path.parent
    else:
        files = sorted([p for p in input_path.rglob("*") if p.is_file()])
        base_input_dir = input_path

    for file_path in files:
        suffix = file_path.suffix.lower()

        if suffix not in {".json", ".jsonl"}:
            continue

        relative_path = file_path.relative_to(base_input_dir)
        out_file = (
            output_path / relative_path
            if output_path.is_dir() or not output_path.suffix
            else output_path
        )

        if input_path.is_file() and output_path.suffix:
            out_file = output_path
        elif input_path.is_file() and not output_path.suffix:
            out_file = output_path / file_path.name

        total_files += 1

        if suffix == ".json":
            total, kept, dropped_url = process_json_file(
                input_path=file_path,
                output_path=out_file,
                text_fields=text_fields,
                unicode_form=unicode_form,
                drop_empty=drop_empty,
                drop_url=drop_url,
            )
        else:
            total, kept, dropped_url = process_jsonl_file(
                input_path=file_path,
                output_path=out_file,
                text_fields=text_fields,
                unicode_form=unicode_form,
                drop_empty=drop_empty,
                drop_url=drop_url,
            )

        total_records += total
        kept_records += kept
        dropped_url_records += dropped_url

        print(
            f"[DONE] {file_path} -> {out_file} | "
            f"total={total} kept={kept} dropped_url={dropped_url}"
        )

    print("=" * 60)
    print("CLEANER SUMMARY")
    print("=" * 60)
    print(f"Files processed : {total_files}")
    print(f"Records total   : {total_records}")
    print(f"Records kept    : {kept_records}")
    print(f"Dropped URL     : {dropped_url_records}")
    print("=" * 60)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Làm sạch văn bản: xóa HTML, normalize unicode, chuẩn hóa khoảng trắng."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="File hoặc thư mục đầu vào, ví dụ raw/ hoặc raw/pubmed_sentences.json",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="File hoặc thư mục đầu ra, ví dụ cleaned/ hoặc cleaned/pubmed_sentences.json",
    )
    parser.add_argument(
        "--fields",
        nargs="*",
        default=None,
        help="Các field text cần làm sạch, ví dụ sentence abstract title en vi",
    )
    parser.add_argument(
        "--unicode-form",
        default="NFKC",
        choices=["NFC", "NFD", "NFKC", "NFKD"],
        help="Kiểu normalize unicode",
    )
    parser.add_argument(
        "--drop-empty",
        action="store_true",
        help="Bỏ record nếu các field text sau khi clean bị rỗng",
    )
    parser.add_argument(
        "--drop-url",
        action="store_true",
        help="Bỏ record nếu bất kỳ field text gốc nào chứa URL/http/https/www/github/huggingface",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Không tìm thấy input: {input_path}")

    text_fields = args.fields if args.fields else infer_default_text_fields()

    process_path(
        input_path=input_path,
        output_path=output_path,
        text_fields=text_fields,
        unicode_form=args.unicode_form,
        drop_empty=args.drop_empty,
        drop_url=args.drop_url,
    )


if __name__ == "__main__":
    main()