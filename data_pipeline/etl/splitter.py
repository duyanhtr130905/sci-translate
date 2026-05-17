from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path
from typing import Any


SUPPORTED_SUFFIXES = {".json", ".jsonl", ".tsv"}


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


def infer_mode_and_fields(sample: dict[str, Any], mode: str) -> tuple[str, list[str]]:
    if mode == "bilingual":
        return mode, ["en", "vi"]
    if mode == "monolingual":
        if "sentence" in sample:
            return mode, ["sentence"]
        if "text" in sample:
            return mode, ["text"]
        return mode, ["sentence"]

    if "en" in sample and "vi" in sample:
        return "bilingual", ["en", "vi"]
    if "sentence" in sample:
        return "monolingual", ["sentence"]
    if "text" in sample:
        return "monolingual", ["text"]
    return "monolingual", ["sentence"]


def load_rows_from_file(input_path: Path) -> list[dict[str, Any]]:
    suffix = input_path.suffix.lower()

    if suffix == ".json":
        data = read_json(input_path)
        if not isinstance(data, list):
            raise ValueError(f"JSON input phải là list các record: {input_path}")
        return [row for row in data if isinstance(row, dict)]

    if suffix == ".jsonl":
        return read_jsonl(input_path)

    if suffix == ".tsv":
        return read_tsv(input_path)

    raise ValueError(f"Chỉ hỗ trợ .json, .jsonl, .tsv: {input_path}")


def load_rows(input_path: Path) -> tuple[list[dict[str, Any]], list[Path]]:
    if input_path.is_file():
        return load_rows_from_file(input_path), [input_path]

    if not input_path.is_dir():
        raise FileNotFoundError(f"Không tìm thấy input: {input_path}")

    files = sorted(
        p for p in input_path.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
    )
    if not files:
        raise ValueError(f"Không tìm thấy file .json/.jsonl/.tsv trong thư mục: {input_path}")

    rows: list[dict[str, Any]] = []
    for file_path in files:
        file_rows = load_rows_from_file(file_path)
        for row in file_rows:
            merged = dict(row)
            merged.setdefault("source_file", file_path.name)
            rows.append(merged)

    return rows, files


def save_rows(output_path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    suffix = output_path.suffix.lower()

    if suffix == ".json":
        write_json(output_path, rows)
    elif suffix == ".jsonl":
        write_jsonl(output_path, rows)
    elif suffix == ".tsv":
        write_tsv(output_path, rows, fields)
    else:
        raise ValueError("Output chỉ hỗ trợ .json, .jsonl, .tsv")


def split_rows(
    rows: list[dict[str, Any]],
    test_ratio: float,
    shuffle: bool,
    seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not rows:
        return [], []

    items = list(rows)

    if shuffle:
        rng = random.Random(seed)
        rng.shuffle(items)

    test_size = int(round(len(items) * test_ratio))
    test_size = max(1, test_size) if len(items) > 1 and test_ratio > 0 else test_size
    test_size = min(test_size, len(items))

    test_rows = items[:test_size]
    train_rows = items[test_size:]

    return train_rows, test_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Chia train/test theo tỷ lệ, mặc định 90/10. Hỗ trợ input là file hoặc cả thư mục."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="File hoặc thư mục đầu vào: .json, .jsonl hoặc .tsv. Ví dụ deduplicated/",
    )
    parser.add_argument("--train", required=True, help="File output train")
    parser.add_argument("--test", required=True, help="File output test")
    parser.add_argument(
        "--mode",
        default="auto",
        choices=["auto", "bilingual", "monolingual"],
        help="Tự nhận diện hoặc ép kiểu dữ liệu",
    )
    parser.add_argument(
        "--test-ratio",
        type=float,
        default=0.10,
        help="Tỷ lệ test, mặc định 0.10",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed để shuffle và tái lập split",
    )
    parser.add_argument(
        "--no-shuffle",
        action="store_true",
        help="Không shuffle trước khi chia",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_path = Path(args.input)
    train_path = Path(args.train)
    test_path = Path(args.test)

    if not input_path.exists():
        raise FileNotFoundError(f"Không tìm thấy input: {input_path}")

    if not (0 <= args.test_ratio <= 1):
        raise ValueError("--test-ratio phải nằm trong [0, 1]")

    rows, source_files = load_rows(input_path)
    if not rows:
        raise ValueError("Không có record hợp lệ trong input.")

    mode, fields = infer_mode_and_fields(rows[0], args.mode)
    train_rows, test_rows = split_rows(
        rows=rows,
        test_ratio=args.test_ratio,
        shuffle=not args.no_shuffle,
        seed=args.seed,
    )

    save_rows(train_path, train_rows, fields)
    save_rows(test_path, test_rows, fields)

    print("=" * 60)
    print("SPLITTER SUMMARY")
    print("=" * 60)
    print(f"Input path     : {input_path}")
    print(f"Source files   : {len(source_files)}")
    for file_path in source_files:
        print(f"  - {file_path}")
    print(f"Mode           : {mode}")
    print(f"Train file     : {train_path}")
    print(f"Test file      : {test_path}")
    print(f"Total records  : {len(rows)}")
    print(f"Train size     : {len(train_rows)}")
    print(f"Test size      : {len(test_rows)}")
    print(f"Test ratio     : {args.test_ratio}")
    print(f"Shuffle        : {not args.no_shuffle}")
    print(f"Seed           : {args.seed}")
    print("=" * 60)


if __name__ == "__main__":
    main()
