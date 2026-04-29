#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from typing import Iterable

from neo4j import GraphDatabase
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "corpus"

TRAIN_FILE = CORPUS_DIR / "train.tsv"
TEST_FILE = CORPUS_DIR / "test.tsv"

MIN_TRAIN_ROWS = 50_000
MIN_TEST_ROWS = 5_000
MIN_NEO4J_NODES = 500
MIN_NEO4J_EDGES = 1_000
MIN_LANG_ACCURACY = 95.0


def print_pass(msg: str) -> None:
    print(f"[PASS] {msg}")


def print_fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def count_non_empty_lines(path: Path) -> int:
    if not path.exists():
        return 0

    total = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                total += 1
    return total


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise EnvironmentError(
            "Biến môi trường DATABASE_URL chưa được set. "
            "Ví dụ: DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname"
        )
    return url


def check_postgres() -> tuple[bool, int]:
    db_url = get_database_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        row_count = conn.execute(
            text("SELECT COUNT(*) FROM translation_memory")
        ).scalar_one()

    return True, int(row_count)


def get_neo4j_config() -> tuple[str, str, str]:
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")

    missing = []
    if not uri:
        missing.append("NEO4J_URI")
    if not user:
        missing.append("NEO4J_USER")
    if not password:
        missing.append("NEO4J_PASSWORD")
    if missing:
        raise EnvironmentError(
            f"Thiếu biến môi trường: {', '.join(missing)}. "
            "Hãy set NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD."
        )

    return uri, user, password


def check_neo4j() -> tuple[int, int, bool]:
    uri, user, password = get_neo4j_config()
    driver = GraphDatabase.driver(uri, auth=(user, password))

    try:
        with driver.session() as session:
            total_nodes = session.run(
                "MATCH (t:Term) RETURN count(t) AS total"
            ).single()["total"]

            total_edges = session.run(
                "MATCH ()-[r]->() RETURN count(r) AS total"
            ).single()["total"]

            rag_found = session.run(
                """
                MATCH (t:Term)
                WHERE toLower(replace(t.term, '"', '')) = 'rag'
                RETURN count(t) > 0 AS found
                """
            ).single()["found"]
    finally:
        driver.close()

    return int(total_nodes), int(total_edges), bool(rag_found)


def iter_tsv_pairs(path: Path, limit: int = 1000) -> Iterable[tuple[str, str]]:
    count = 0
    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if not row:
                continue

            if len(row) >= 3:
                en_text = row[1].strip()
                vi_text = row[2].strip()
            elif len(row) >= 2:
                en_text = row[0].strip()
                vi_text = row[1].strip()
            else:
                continue

            if not en_text or not vi_text:
                continue

            yield en_text, vi_text
            count += 1
            if count >= limit:
                break


def estimate_language_accuracy(path: Path, sample_size: int = 500) -> float:
    try:
        from langdetect import detect
    except Exception:
        return -1.0

    checked = 0
    correct = 0

    for en_text, vi_text in iter_tsv_pairs(path, limit=sample_size):
        try:
            if len(en_text) < 10 or len(vi_text) < 10:
                continue

            en_lang = detect(en_text)
            vi_lang = detect(vi_text)

            checked += 1
            if en_lang == "en" and vi_lang == "vi":
                correct += 1
        except Exception:
            continue

    if checked == 0:
        return 0.0

    return round((correct / checked) * 100, 1)


def main() -> int:
    ok = True

    train_rows = count_non_empty_lines(TRAIN_FILE)
    if train_rows >= MIN_TRAIN_ROWS:
        print_pass(f"corpus/train.tsv: {train_rows:,} dòng")
    else:
        print_fail(f"corpus/train.tsv: {train_rows:,} dòng, cần >= {MIN_TRAIN_ROWS:,}")
        ok = False

    test_rows = count_non_empty_lines(TEST_FILE)
    if test_rows >= MIN_TEST_ROWS:
        print_pass(f"corpus/test.tsv:  {test_rows:,} dòng")
    else:
        print_fail(f"corpus/test.tsv:  {test_rows:,} dòng, cần >= {MIN_TEST_ROWS:,}")
        ok = False

    try:
        _, db_rows = check_postgres()
        print_pass(
            f"PostgreSQL: kết nối OK, bảng translation_memory: {db_rows:,} rows"
        )
    except Exception as e:
        print_fail(f"PostgreSQL: lỗi kết nối hoặc query bảng translation_memory -> {e}")
        ok = False

    try:
        neo4j_nodes, neo4j_edges, rag_found = check_neo4j()

        if neo4j_nodes >= MIN_NEO4J_NODES and neo4j_edges >= MIN_NEO4J_EDGES:
            print_pass(f"Neo4j: {neo4j_nodes:,} nodes, {neo4j_edges:,} edges")
        else:
            print_fail(
                f"Neo4j: {neo4j_nodes:,} nodes, {neo4j_edges:,} edges "
                f"(cần >= {MIN_NEO4J_NODES} nodes và >= {MIN_NEO4J_EDGES} edges)"
            )
            ok = False

        if rag_found:
            print_pass("Neo4j: term 'RAG' tồn tại")
        else:
            print_fail("Neo4j: không tìm thấy term 'RAG'")
            ok = False

    except Exception as e:
        print_fail(f"Neo4j: lỗi kết nối hoặc query -> {e}")
        ok = False

    lang_acc = estimate_language_accuracy(TRAIN_FILE, sample_size=500)
    if lang_acc < 0:
        print_fail("Language detection accuracy: chưa tính được (thiếu package langdetect)")
        ok = False
    elif lang_acc >= MIN_LANG_ACCURACY:
        print_pass(f"Language detection accuracy: {lang_acc:.1f}%")
    else:
        print_fail(
            f"Language detection accuracy: {lang_acc:.1f}% (cần >= {MIN_LANG_ACCURACY:.1f}%)"
        )
        ok = False

    if ok:
        print("✅ Sẵn sàng bàn giao cho TV2!")
        return 0

    print("❌ Chưa đạt checklist bàn giao.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())