import argparse
import os
import re
import sys
from typing import Optional

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError


def normalize_text(value: str) -> str:
    return " ".join((value or "").strip().split())


def build_term_key(term: str, language: str) -> str:
    return f"{language}:{normalize_text(term).lower()}"


def split_multi_value(raw: str) -> list[str]:
    raw = normalize_text(raw)
    if not raw:
        return []

    if ";" in raw or "|" in raw:
        parts = re.split(r"[;|]+", raw)
    else:
        parts = re.split(r",+", raw)

    result = []
    seen = set()
    for part in parts:
        v = normalize_text(part)
        if v and v.lower() not in seen:
            result.append(v)
            seen.add(v.lower())
    return result


def get_neo4j_config(uri: Optional[str], user: Optional[str], password: Optional[str]):
    return (
        uri or os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user or os.getenv("NEO4J_USER", "neo4j"),
        password or os.getenv("NEO4J_PASSWORD", "password"),
    )


FETCH_ROWS_QUERY = """
MATCH (row:ImportRow)-[:HAS_TERM {role: 'source'}]->(en:Term {language: 'en'})
MATCH (row)-[:HAS_TERM {role: 'target'}]->(vi:Term {language: 'vi'})
RETURN
    en.term AS term_en,
    vi.term AS term_vi,
    row.synonyms_en_raw AS synonyms_en_raw,
    row.parent_term_en_raw AS parent_term_en_raw
"""


MERGE_TERM_QUERY = """
MERGE (t:Term {key: $key})
ON CREATE SET
    t.term = $term,
    t.language = $language
RETURN t
"""


MERGE_TRANSLATION_QUERY = """
MATCH (a:Term {key: $source_key})
MATCH (b:Term {key: $target_key})
MERGE (a)-[:TRANSLATION_OF]->(b)
"""


MERGE_SYNONYM_QUERY = """
MATCH (a:Term {key: $term_key})
MATCH (b:Term {key: $synonym_key})
MERGE (a)-[:SYNONYM_OF]->(b)
MERGE (b)-[:SYNONYM_OF]->(a)
"""


MERGE_HYPERNYM_QUERY = """
MATCH (a:Term {key: $term_key})
MATCH (b:Term {key: $parent_key})
MERGE (a)-[:HYPERNYM_OF]->(b)
"""


def merge_term(session, term: str, language: str) -> str:
    key = build_term_key(term, language)
    session.run(
        MERGE_TERM_QUERY,
        {"key": key, "term": normalize_text(term), "language": language},
    )
    return key


def build_relations(driver):
    with driver.session() as session:
        records = list(session.run(FETCH_ROWS_QUERY))

        for record in records:
            term_en = normalize_text(record["term_en"])
            term_vi = normalize_text(record["term_vi"])

            if not term_en or not term_vi:
                continue

            en_key = merge_term(session, term_en, "en")
            vi_key = merge_term(session, term_vi, "vi")

            session.run(MERGE_TRANSLATION_QUERY, {"source_key": en_key, "target_key": vi_key})
            session.run(MERGE_TRANSLATION_QUERY, {"source_key": vi_key, "target_key": en_key})

            for synonym in split_multi_value(record["synonyms_en_raw"]):
                synonym_key = merge_term(session, synonym, "en")
                session.run(MERGE_SYNONYM_QUERY, {"term_key": en_key, "synonym_key": synonym_key})

            parent = normalize_text(record["parent_term_en_raw"])
            if parent:
                parent_key = merge_term(session, parent, "en")
                session.run(MERGE_HYPERNYM_QUERY, {"term_key": en_key, "parent_key": parent_key})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", default=None)
    parser.add_argument("--user", default=None)
    parser.add_argument("--password", default=None)
    args = parser.parse_args()

    try:
        uri, user, password = get_neo4j_config(args.uri, args.user, args.password)
        driver = GraphDatabase.driver(uri, auth=(user, password))
        build_relations(driver)
        driver.close()
        print("[DONE] Relations created.")
        return 0
    except (Neo4jError, ValueError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())