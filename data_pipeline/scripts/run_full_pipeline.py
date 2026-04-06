#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable

COLLECTORS_DIR = ROOT / "collectors"
ETL_DIR = ROOT / "etl"
KG_DIR = ROOT / "kg"

RAW_DIR = ROOT / "raw"
CLEANED_DIR = ROOT / "cleaned"
ALIGNED_DIR = ROOT / "aligned"
CORPUS_DIR = ROOT / "corpus"
SEED_DIR = KG_DIR / "seed_data"


def run_cmd(cmd: list[str], title: str) -> None:
    print(f"\n=== {title} ===")
    print(" ".join(map(str, cmd)))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(f"[ERROR] Step failed: {title}")


def ensure_dirs() -> None:
    for path in [RAW_DIR, CLEANED_DIR, ALIGNED_DIR, CORPUS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def get_seed_csv_files() -> list[Path]:
    preferred = [
        SEED_DIR / "cs_terms_fixed.csv",
        SEED_DIR / "nlp_terms_fixed.csv",
        SEED_DIR / "bio_terms_fixed.csv",
        SEED_DIR / "physics_terms_fixed.csv",
    ]
    fallback = [
        SEED_DIR / "cs_terms.csv",
        SEED_DIR / "nlp_terms.csv",
        SEED_DIR / "bio_terms.csv",
        SEED_DIR / "physics_terms.csv",
    ]

    files: list[Path] = []
    for fixed_file, normal_file in zip(preferred, fallback):
        if fixed_file.exists():
            files.append(fixed_file)
        elif normal_file.exists():
            files.append(normal_file)

    return files


def run_align_all() -> list[Path]:
    """
    aligner.py của bạn yêu cầu:
      --en <file_en> --vi <file_vi> --output <aligned_file>
    nên phải chạy theo từng cặp file.
    """
    pairs = [
        ("acl_sentences_en.json", "acl_sentences_vi.json", "acl_aligned.tsv"),
        ("arxiv_sentences_en.json", "arxiv_sentences_vi.json", "arxiv_aligned.tsv"),
        ("pubmed_sentences_en.json", "pubmed_sentences_vi.json", "pubmed_aligned.tsv"),
    ]

    aligned_files: list[Path] = []

    for en_name, vi_name, out_name in pairs:
        en_path = CLEANED_DIR / en_name
        vi_path = CLEANED_DIR / vi_name
        out_path = ALIGNED_DIR / out_name

        if not en_path.exists() or not vi_path.exists():
            print(f"[WARN] Skip missing pair: {en_path.name} / {vi_path.name}")
            continue

        run_cmd(
            [
                PYTHON,
                str(ETL_DIR / "aligner.py"),
                "--en",
                str(en_path),
                "--vi",
                str(vi_path),
                "--output",
                str(out_path),
            ],
            f"Align {en_name} + {vi_name}",
        )
        aligned_files.append(out_path)

    if not aligned_files:
        raise SystemExit("[ERROR] No aligned files were generated.")

    return aligned_files


def merge_aligned_files(files: list[Path]) -> Path:
    """
    Gộp các file aligned thành 1 file all.tsv trước khi deduplicate.
    """
    merged_path = ALIGNED_DIR / "all.tsv"
    total_lines = 0

    with merged_path.open("w", encoding="utf-8") as fout:
        for file_path in files:
            if not file_path.exists():
                continue

            with file_path.open("r", encoding="utf-8") as fin:
                for line in fin:
                    if line.strip():
                        fout.write(line)
                        total_lines += 1

    print(f"[DONE] Merged aligned files -> {merged_path} | total_lines={total_lines}")
    return merged_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full Data Pipeline for TV4.")
    parser.add_argument(
        "--with-collectors",
        action="store_true",
        help="Run collectors before ETL steps.",
    )
    parser.add_argument(
        "--skip-db-load",
        action="store_true",
        help="Skip loading train.tsv into PostgreSQL.",
    )
    parser.add_argument(
        "--skip-kg",
        action="store_true",
        help="Skip Neo4j seed and relation building.",
    )
    parser.add_argument(
        "--has-header",
        action="store_true",
        help="Pass header flag to loader.py if train.tsv has header.",
    )
    args = parser.parse_args()

    ensure_dirs()

    if args.with_collectors:
        run_cmd(
            [
                PYTHON,
                str(COLLECTORS_DIR / "arxiv_collector.py"),
                "--domain",
                "cs.CL",
                "--max",
                "20000",
            ],
            "Collect arXiv data",
        )
        run_cmd(
            [
                PYTHON,
                str(COLLECTORS_DIR / "pubmed_collector.py"),
                "--domain",
                "NLP",
                "--max",
                "15000",
            ],
            "Collect PubMed data",
        )
        run_cmd(
            [
                PYTHON,
                str(COLLECTORS_DIR / "acl_collector.py"),
                "--query",
                "machine translation",
                "--max-results",
                "15000",
            ],
            "Collect ACL data",
        )

    run_cmd(
        [
            PYTHON,
            str(ETL_DIR / "cleaner.py"),
            "--input",
            str(RAW_DIR),
            "--output",
            str(CLEANED_DIR),
        ],
        "Clean text",
    )

    aligned_files = run_align_all()
    merged_aligned = merge_aligned_files(aligned_files)

    run_cmd(
        [
            PYTHON,
            str(ETL_DIR / "deduplicator.py"),
            "--input",
            str(merged_aligned),
            "--output",
            str(CORPUS_DIR / "all.tsv"),
        ],
        "Deduplicate pairs",
    )

    run_cmd(
        [
            PYTHON,
            str(ETL_DIR / "splitter.py"),
            "--input",
            str(CORPUS_DIR / "all.tsv"),
            "--train",
            str(CORPUS_DIR / "train.tsv"),
            "--test",
            str(CORPUS_DIR / "test.tsv"),
        ],
        "Split train/test",
    )

    if not args.skip_db_load:
        loader_cmd = [
            PYTHON,
            str(ETL_DIR / "loader.py"),
            "--file",
            str(CORPUS_DIR / "train.tsv"),
        ]
        if args.has_header:
            loader_cmd.append("--has-header")

        run_cmd(loader_cmd, "Load train.tsv into PostgreSQL")

    if not args.skip_kg:
        kg_files = get_seed_csv_files()
        if not kg_files:
            raise SystemExit("[ERROR] No KG seed CSV files found in kg/seed_data")

        for csv_file in kg_files:
            run_cmd(
                [
                    PYTHON,
                    str(KG_DIR / "term_importer.py"),
                    "--csv",
                    str(csv_file),
                ],
                f"Seed KG from {csv_file.name}",
            )

        run_cmd(
            [PYTHON, str(KG_DIR / "relation_builder.py")],
            "Build KG relations",
        )

    print("\n✅ Full pipeline completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())