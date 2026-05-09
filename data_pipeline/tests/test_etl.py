from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


THIS_FILE = Path(__file__).resolve()
TESTS_DIR = THIS_FILE.parent
PIPELINE_ROOT = TESTS_DIR.parent
ETL_DIR = PIPELINE_ROOT / "etl"
VALIDATORS_DIR = PIPELINE_ROOT / "validators"

# Fallback for running this test file standalone from any location.
FALLBACK_DIR = Path(__file__).resolve().parent
if not ETL_DIR.exists():
    ETL_DIR = FALLBACK_DIR
if not VALIDATORS_DIR.exists():
    VALIDATORS_DIR = FALLBACK_DIR

for path in (str(ETL_DIR), str(VALIDATORS_DIR), str(PIPELINE_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

import cleaner  # type: ignore  # noqa: E402
import aligner  # type: ignore  # noqa: E402
import deduplicator  # type: ignore  # noqa: E402


def test_clean_text_removes_html_latex_and_normalizes_whitespace() -> None:
    raw = '  <b>Hello</b> \\textbf{World}  3.14  //  \\"quoted\\"  '
    cleaned = cleaner.clean_text(raw)

    assert "<b>" not in cleaned
    assert "\\" not in cleaned
    assert "//" not in cleaned
    assert '"' not in cleaned
    assert cleaned == "Hello World 3.14 quoted"


def test_clean_record_cleans_only_requested_fields() -> None:
    record = {
        "id": 1,
        "sentence": "<i>Machine</i>   learning",
        "note": "Keep   this raw",
    }
    cleaned = cleaner.clean_record(record, text_fields=["sentence"])

    assert cleaned["sentence"] == "Machine learning"
    assert cleaned["note"] == "Keep   this raw"


def test_align_records_keeps_only_valid_shared_ids() -> None:
    en_records = [
        {"id": 1, "sentence": "Machine learning improves scientific translation quality significantly."},
        {"id": 2, "sentence": "Short."},
        {"id": 3, "sentence": "This sentence is valid in English but the paired text will be too long."},
    ]
    vi_records = [
        {"id": 1, "sentence": "Học máy cải thiện đáng kể chất lượng dịch tài liệu khoa học."},
        {"id": 2, "sentence": "Ngắn."},
        {
            "id": 3,
            "sentence": "Đây là một câu tiếng Việt rất dài được lặp lại nhiều lần để tạo ra chênh lệch độ dài lớn lớn lớn lớn lớn lớn lớn lớn lớn.",
        },
        {"id": 4, "sentence": "Câu này không có phía tiếng Anh tương ứng."},
    ]

    aligned, stats = aligner.align_records(
        en_records=en_records,
        vi_records=vi_records,
        min_tokens=5,
        max_tokens=100,
        min_char_len=10,
        max_length_ratio=1.9,
    )

    assert len(aligned) == 1
    assert aligned[0]["id"] == 1
    assert aligned[0]["en"].startswith("Machine learning")
    assert aligned[0]["vi"].startswith("Học máy")
    assert stats["shared_ids"] == 3
    assert stats["kept"] == 1
    assert stats["dropped_too_short_chars"] >= 1 or stats["dropped_too_short_tokens"] >= 1
    assert stats["dropped_length_ratio"] >= 1


def test_deduplicate_rows_bilingual_removes_duplicates() -> None:
    rows = [
        {"id": 1, "en": "The model was trained on data.", "vi": "Mô hình được huấn luyện trên dữ liệu."},
        {"id": 2, "en": "The model was trained on data.", "vi": "Mô hình được huấn luyện trên dữ liệu."},
        {"id": 3, "en": "The system uses retrieval.", "vi": "Hệ thống sử dụng truy hồi."},
    ]

    kept, dup_count, empty_count = deduplicator.deduplicate_rows(
        rows=rows,
        fields=["en", "vi"],
        drop_empty=True,
    )

    assert len(kept) == 2
    assert dup_count == 1
    assert empty_count == 0
    assert kept[0]["id"] == 1
    assert kept[1]["id"] == 3


def test_process_file_tsv_roundtrip(tmp_path: Path) -> None:
    input_path = tmp_path / "aligned.tsv"
    output_path = tmp_path / "dedup.tsv"
    input_path.write_text(
        "The model was trained on data.\tMô hình được huấn luyện trên dữ liệu.\n"
        "The model was trained on data.\tMô hình được huấn luyện trên dữ liệu.\n"
        "The system uses retrieval.\tHệ thống sử dụng truy hồi.\n",
        encoding="utf-8",
    )

    deduplicator.process_file(
        input_path=input_path,
        output_path=output_path,
        mode="bilingual",
        fields=["en", "vi"],
        unicode_form="NFKC",
        lower=False,
        drop_empty=True,
    )

    lines = output_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("The model was trained on data.\t")
    assert lines[1].startswith("The system uses retrieval.\t")
