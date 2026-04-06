import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Optional

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError


def normalize_text(value: str) -> str:
    return " ".join((value or "").strip().split())


def build_term_key(term: str, language: str) -> str:
    return f"{language}:{normalize_text(term).lower()}"


def get_value(row: dict, *keys: str) -> str:
    lowered = {str(k).strip().lower(): v for k, v in row.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def get_neo4j_config(uri: Optional[str], user: Optional[str], password: Optional[str]):
    return (
        uri or os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user or os.getenv("NEO4J_USER", "neo4j"),
        password or os.getenv("NEO4J_PASSWORD", "password"),
    )


CREATE_CONSTRAINTS = [
    "CREATE CONSTRAINT term_key_unique IF NOT EXISTS FOR (t:Term) REQUIRE t.key IS UNIQUE",
    "CREATE CONSTRAINT domain_name_unique IF NOT EXISTS FOR (d:Domain) REQUIRE d.name IS UNIQUE",
    "CREATE CONSTRAINT import_row_unique IF NOT EXISTS FOR (r:ImportRow) REQUIRE r.row_key IS UNIQUE",
]


UPSERT_ROW_QUERY = """
MERGE (row:ImportRow {row_key: $row_key})
SET
    row.file_name = $file_name,
    row.line_no = $line_no,
    row.domain = $domain,
    row.subdomain = $subdomain,
    row.parent_term_en_raw = $parent_term_en_raw,
    row.synonyms_en_raw = $synonyms_en_raw

WITH row
MERGE (en:Term {key: $en_key})
ON CREATE SET
    en.term = $term_en,
    en.language = 'en',
    en.definition = $definition_en
ON MATCH SET
    en.term = coalesce(en.term, $term_en),
    en.definition = CASE
        WHEN en.definition IS NULL OR en.definition = '' THEN $definition_en
        ELSE en.definition
    END

MERGE (vi:Term {key: $vi_key})
ON CREATE SET
    vi.term = $term_vi,
    vi.language = 'vi',
    vi.definition = $definition_vi
ON MATCH SET
    vi.term = coalesce(vi.term, $term_vi),
    vi.definition = CASE
        WHEN vi.definition IS NULL OR vi.definition = '' THEN $definition_vi
        ELSE vi.definition
    END

MERGE (row)-[:HAS_TERM {role: 'source'}]->(en)
MERGE (row)-[:HAS_TERM {role: 'target'}]->(vi)

FOREACH (_ IN CASE WHEN $domain <> '' THEN [1] ELSE [] END |
    MERGE (d:Domain {name: $domain})
    MERGE (en)-[:BELONGS_TO]->(d)
    MERGE (vi)-[:BELONGS_TO]->(d)
)

FOREACH (_ IN CASE WHEN $subdomain <> '' THEN [1] ELSE [] END |
    MERGE (sd:Subdomain {name: $subdomain})
    MERGE (en)-[:IN_SUBDOMAIN]->(sd)
    MERGE (vi)-[:IN_SUBDOMAIN]->(sd)
)
"""


def ensure_constraints(driver):
    with driver.session() as session:
        for query in CREATE_CONSTRAINTS:
            session.run(query)


def import_csv(driver, csv_path: str) -> int:
    total = 0
    file_name = Path(csv_path).name

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        with driver.session() as session:
            for line_no, row in enumerate(reader, start=2):
                term_en = get_value(row, "term_en", "en")
                term_vi = get_value(row, "term_vi", "vi")

                if not term_en or not term_vi:
                    continue

                params = {
                    "row_key": f"{file_name}:{line_no}",
                    "file_name": file_name,
                    "line_no": line_no,
                    "term_en": normalize_text(term_en),
                    "term_vi": normalize_text(term_vi),
                    "en_key": build_term_key(term_en, "en"),
                    "vi_key": build_term_key(term_vi, "vi"),
                    "domain": normalize_text(get_value(row, "domain")),
                    "subdomain": normalize_text(get_value(row, "subdomain")),
                    "parent_term_en_raw": normalize_text(get_value(row, "parent_term_en", "hypernym_en")),
                    "synonyms_en_raw": normalize_text(get_value(row, "synonyms_en")),
                    "definition_en": normalize_text(get_value(row, "definition_en")),
                    "definition_vi": normalize_text(get_value(row, "definition_vi")),
                }

                session.run(UPSERT_ROW_QUERY, params)
                total += 1

    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--uri", default=None)
    parser.add_argument("--user", default=None)
    parser.add_argument("--password", default=None)
    args = parser.parse_args()

    try:
        uri, user, password = get_neo4j_config(args.uri, args.user, args.password)
        driver = GraphDatabase.driver(uri, auth=(user, password))
        ensure_constraints(driver)
        total = import_csv(driver, args.csv)
        driver.close()
        print(f"[DONE] Imported rows: {total}")
        return 0
    except (Neo4jError, OSError, ValueError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())