from .neo4j_client import Neo4jClient
from .cypher_queries import GET_TERMS_IN_TEXT
import re

VI_PATTERN = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]"
)

class KGQueryService:
    def __init__(self):
        self.client = Neo4jClient()

    def _detect_lang(self, text: str) -> tuple[str, str]:
        if VI_PATTERN.search(text):
            return "vi", "en"
        return "en", "vi"

    def _extract_candidate_terms(self, text: str) -> list[str]:
        """
        Extract n-grams (1-3 words) as candidate term lookups.
        KG lookup works on exact term match so we try all subphrases.
        """
        words = text.lower().split()
        candidates = []
        for n in range(1, 4):          
            for i in range(len(words) - n + 1):
                candidates.append(" ".join(words[i:i+n]))
        return candidates

    def get_context_for_translation(self, text: str) -> dict | None:
        """
        Returns {source_term: target_term} dict for engine._build_kg_block.
        Scans all n-gram candidates in the text against the KG.
        """
        source_lang, target_lang = self._detect_lang(text)
        candidates = self._extract_candidate_terms(text)

        if not candidates:
            return None

        results = self.client.query(
            GET_TERMS_IN_TEXT,
            {
                "term_list": candidates,
                "source_lang": source_lang,
                "target_lang": target_lang,
            }
        )

        if not results:
            return None

        kg_dict = {
            row["source_term"]: row["target_term"]
            for row in results
            if row.get("source_term") and row.get("target_term")
        }

        return kg_dict if kg_dict else None