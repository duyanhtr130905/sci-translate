from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


THIS_FILE = Path(__file__).resolve()
TESTS_DIR = THIS_FILE.parent
PIPELINE_ROOT = TESTS_DIR.parent
VALIDATORS_DIR = PIPELINE_ROOT / "validators"

FALLBACK_DIR = Path(__file__).resolve().parent
if not VALIDATORS_DIR.exists():
    VALIDATORS_DIR = FALLBACK_DIR

for path in (str(VALIDATORS_DIR), str(PIPELINE_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

import quality_validator  # type: ignore  # noqa: E402


SCHEMA_VALIDATOR_PATHS = [
    VALIDATORS_DIR / "schema_validator.py",
    FALLBACK_DIR / "schema_validator.py",
]


def _load_schema_validator():
    for path in SCHEMA_VALIDATOR_PATHS:
        if path.exists():
            spec = importlib.util.spec_from_file_location("schema_validator", path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module
    return None


schema_validator = _load_schema_validator()


def test_quality_validator_passes_clean_bilingual_tsv(tmp_path: Path) -> None:
    file_path = tmp_path / "train.tsv"
    file_path.write_text(
        "Machine learning improves translation quality for scientific documents.\t"
        "Học máy cải thiện chất lượng dịch cho các tài liệu khoa học.\n"
        "The retrieval module finds relevant terminology in the corpus.\t"
        "Mô-đun truy hồi tìm các thuật ngữ liên quan trong kho ngữ liệu.\n",
        encoding="utf-8",
    )

    ok, stats = quality_validator.validate_quality(
        path=file_path,
        min_tokens=5,
        max_tokens=100,
        min_confidence=0.80,
    )

    assert ok is True
    assert stats["total_lines"] == 2
    assert stats["valid_lines"] == 2
    assert stats["invalid_lines"] == 0
    assert stats["bad_length"] == 0
    assert stats["bad_language"] == 0


def test_quality_validator_flags_bad_language(tmp_path: Path) -> None:
    file_path = tmp_path / "train.tsv"
    file_path.write_text(
        "Machine learning improves translation quality for science.\t"
        "Machine learning improves translation quality for science.\n",
        encoding="utf-8",
    )

    ok, stats = quality_validator.validate_quality(
        path=file_path,
        min_tokens=5,
        max_tokens=100,
        min_confidence=0.80,
    )

    assert ok is False
    assert stats["total_lines"] == 1
    assert stats["invalid_lines"] == 1
    assert stats["bad_language"] == 1
    assert any("language mismatch" in err for err in stats["errors"])


def test_quality_validator_flags_bad_length(tmp_path: Path) -> None:
    file_path = tmp_path / "train.tsv"
    file_path.write_text(
        "Too short.\tQuá ngắn.\n",
        encoding="utf-8",
    )

    ok, stats = quality_validator.validate_quality(
        path=file_path,
        min_tokens=5,
        max_tokens=100,
        min_confidence=0.80,
    )

    assert ok is False
    assert stats["total_lines"] == 1
    assert stats["invalid_lines"] == 1
    assert stats["bad_length"] == 1
    assert any("token_count out of range" in err for err in stats["errors"])


@pytest.mark.skipif(schema_validator is None, reason="schema_validator.py chưa có trong project")
def test_schema_validator_accepts_valid_two_column_tsv(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.tsv"
    file_path.write_text(
        "Machine learning is useful.\tHọc máy rất hữu ích.\n"
        "The corpus was cleaned carefully.\tKho ngữ liệu đã được làm sạch cẩn thận.\n",
        encoding="utf-8",
    )

    # Hỗ trợ 2 kiểu API phổ biến.
    if hasattr(schema_validator, "validate_tsv_schema"):
        ok, stats = schema_validator.validate_tsv_schema(file_path)
    elif hasattr(schema_validator, "validate_schema"):
        ok, stats = schema_validator.validate_schema(file_path)
    else:
        pytest.skip("schema_validator.py không có hàm validate_tsv_schema/validate_schema")

    assert ok is True
    assert isinstance(stats, dict)


@pytest.mark.skipif(schema_validator is None, reason="schema_validator.py chưa có trong project")
def test_schema_validator_rejects_invalid_column_count(tmp_path: Path) -> None:
    file_path = tmp_path / "bad.tsv"
    file_path.write_text(
        "Only one column here\n"
        "EN\tVI\textra\n",
        encoding="utf-8",
    )

    if hasattr(schema_validator, "validate_tsv_schema"):
        ok, stats = schema_validator.validate_tsv_schema(file_path)
    elif hasattr(schema_validator, "validate_schema"):
        ok, stats = schema_validator.validate_schema(file_path)
    else:
        pytest.skip("schema_validator.py không có hàm validate_tsv_schema/validate_schema")

    assert ok is False
    assert isinstance(stats, dict)
