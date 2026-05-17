from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter
from pathlib import Path


TOKEN_RE = re.compile(r"\S+")

DOMAIN_KEYWORDS = {
    "nlp_ai": ["translation", "language model", "llm", "token", "embedding", "nlp", "rag", "bert", "transformer"],
    "computer_science": ["database", "algorithm", "sql", "compiler", "software", "network", "system", "security"],
    "biology": ["gene", "protein", "cell", "clinical", "biomedical", "disease", "antibody", "enzyme"],
    "physics": ["quantum", "signal", "wave", "optics", "field", "thermo", "particle", "motion"],
}


def token_count(text: str) -> int:
    return len(TOKEN_RE.findall(text or ""))


def infer_domain(en: str, vi: str) -> str:
    text = f"{en} {vi}".lower()
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        scores[domain] = sum(1 for kw in keywords if kw in text)

    best_domain, best_score = max(scores.items(), key=lambda x: x[1])
    return best_domain if best_score > 0 else "other"


def parse_tsv(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) != 2:
                continue
            rows.append((row[0].strip(), row[1].strip()))
    return rows


def build_report(path: Path) -> dict:
    rows = parse_tsv(path)
    total_pairs = len(rows)

    en_lengths = [token_count(en) for en, _ in rows]
    vi_lengths = [token_count(vi) for _, vi in rows]
    domains = Counter(infer_domain(en, vi) for en, vi in rows)

    report = {
        "file": str(path),
        "total_pairs": total_pairs,
        "avg_en_length": round(sum(en_lengths) / total_pairs, 2) if total_pairs else 0,
        "avg_vi_length": round(sum(vi_lengths) / total_pairs, 2) if total_pairs else 0,
        "min_en_length": min(en_lengths) if en_lengths else 0,
        "max_en_length": max(en_lengths) if en_lengths else 0,
        "min_vi_length": min(vi_lengths) if vi_lengths else 0,
        "max_vi_length": max(vi_lengths) if vi_lengths else 0,
        "domain_distribution": dict(domains),
    }
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="In báo cáo: tổng cặp, avg length, domain dist.")
    parser.add_argument("--file", required=True, help="Đường dẫn file TSV")
    parser.add_argument("--json-out", default=None, help="Xuất thêm báo cáo JSON")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = Path(args.file)

    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {path}")

    report = build_report(path)

    print("=" * 60)
    print("STATS REPORTER")
    print("=" * 60)
    print(f"File             : {report['file']}")
    print(f"Total pairs      : {report['total_pairs']}")
    print(f"Avg EN length    : {report['avg_en_length']}")
    print(f"Avg VI length    : {report['avg_vi_length']}")
    print(f"Min EN length    : {report['min_en_length']}")
    print(f"Max EN length    : {report['max_en_length']}")
    print(f"Min VI length    : {report['min_vi_length']}")
    print(f"Max VI length    : {report['max_vi_length']}")
    print("Domain dist      :")
    for domain, count in sorted(report["domain_distribution"].items(), key=lambda x: (-x[1], x[0])):
        print(f"  - {domain}: {count}")
    print("=" * 60)

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"[DONE] JSON report -> {out_path}")


if __name__ == "__main__":
    main()
