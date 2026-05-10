import os
import sys
import csv
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AI_SERVICE_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, AI_SERVICE_DIR)

from sacrebleu.metrics import BLEU

from models.ollama_engine import OllamaEngine
from models.ollama_config import OllamaConfig

TEST_DATA_PATH = os.getenv(
    "TEST_DATA_PATH",
    os.path.join(AI_SERVICE_DIR, "..", "data_pipeline", "corpus", "test.tsv"),
)
MAX_SAMPLES = int(os.getenv("BLEU_MAX_SAMPLES", "10"))
DIRECTION = os.getenv("BLEU_DIRECTION", "en->vi")


def evaluate(test_data_path: str, direction: str, max_samples: int):
    test_path = Path(test_data_path)
    if not test_path.exists():
        raise FileNotFoundError(f"Test data not found: {test_path}")

    bleu = BLEU(effective_order=True)
    engine = OllamaEngine(config=OllamaConfig())

    all_references = []
    all_hypotheses = []
    sentence_scores = []
    skipped = 0
    total_cases = 0

    print(f"File     : {test_data_path}")
    print(f"Direction: {direction}")
    print(f"Samples  : {max_samples}")
    print("-" * 60)

    with open(test_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")

        for row in reader:
            if total_cases >= max_samples:
                break

            # Validate row
            if len(row) < 2:
                skipped += 1
                continue

            src_text = row[0].strip()
            ref_text = row[1].strip()

            if not src_text or not ref_text:
                skipped += 1
                continue

            try:
                candidate = engine.translate(
                    src_text,
                    direction=direction,
                )

                # Skip error output
                if not candidate or candidate.startswith("Error:"):
                    skipped += 1
                    continue

                if not candidate.strip() or not ref_text.strip():
                    skipped += 1
                    continue

                # Sentence BLEU
                score = bleu.sentence_score(candidate, [ref_text]).score

                all_references.append(ref_text)
                all_hypotheses.append(candidate)
                sentence_scores.append(score)
                total_cases += 1

                if total_cases % 10 == 0:
                    running_avg = sum(sentence_scores) / len(sentence_scores)
                    print(f"[{total_cases:>4}/{max_samples}] "
                          f"BLEU: {running_avg:.4f} | "
                          f"Last: {score:.4f} | "
                          f"Src: {src_text[:40]}...")

            except Exception as e:
                print(f"[SKIP] Error: {e}")
                skipped += 1
                continue

    print("-" * 60)

    if total_cases == 0:
        print("No valid samples evaluated.")
        return

    avg_sentence_bleu = sum(sentence_scores) / len(sentence_scores)

    avg_corpus_bleu = bleu.corpus_score(all_hypotheses, [all_references]).score

    print(f"Evaluated      : {total_cases} samples")
    print(f"Skipped        : {skipped} samples")
    print(f"Sentence BLEU  : {avg_sentence_bleu:.4f}")
    print(f"Corpus BLEU    : {avg_corpus_bleu:.4f}")
    print("-" * 60)

    score_to_check = avg_corpus_bleu
    if score_to_check >= 40:
        verdict = "GOOD"
    elif score_to_check >= 30:
        verdict = "ACCEPTABLE"
    elif score_to_check >= 10:
        verdict = "NEEDS IMPROVEMENT"
    else:
        verdict = "POOR"

    print(f"Quality        : {verdict}")
    print("-" * 60)

    ranked = sorted(
        enumerate(sentence_scores),
        key=lambda x: x[1],
        reverse=True
    )
    print("\nTop 3 BEST translations:")
    for idx, sc in ranked[:3]:
        print(f"  Score: {sc:.4f} | {all_hypotheses[idx][:80]}")

    print("\nTop 3 WORST translations:")
    for idx, sc in ranked[-3:]:
        print(f"  Score: {sc:.4f} | {all_hypotheses[idx][:80]}")


if __name__ == "__main__":
    evaluate(
        test_data_path=TEST_DATA_PATH,
        direction=DIRECTION,
        max_samples=MAX_SAMPLES,
    )
