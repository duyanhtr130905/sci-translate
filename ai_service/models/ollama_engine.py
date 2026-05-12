import os
import re

from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from models.ollama_config import MODEL_AI, get_ollama_params
from models.ollama_config import GLOSSARY as STATIC_GLOSSARY


VI_PATTERN = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]"
)


# =========================
# LLM CHAIN
# =========================
def get_chain():
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    params = get_ollama_params()

    llm = OllamaLLM(
        base_url=ollama_url,
        model=MODEL_AI,

        temperature=0.0,
        top_k=10,
        top_p=1.0,
        repeat_penalty=1.1,

        num_ctx=4096,
        num_gpu=params["num_gpu"],
        num_thread=params["num_thread"],

        stop=["### INPUT", "Source (", "---"],
    )

    # Template đầy đủ — cho câu dài hoặc từ có trong glossary
    full_template = """### SYSTEM
You are a professional translation engine. Output ONLY the translation — no labels, no explanation, no punctuation changes.

### MANDATORY GLOSSARY (you MUST use these exact translations if the term appears in source):
{glossary}

### EXAMPLES (style reference only):
{examples}

### INPUT
Source ({source_lang}): {input}

### OUTPUT
{target_lang} translation (use MANDATORY GLOSSARY terms exactly):"""

    # Template đơn giản — cho từ đơn không có trong glossary
    simple_template = """### SYSTEM
You are a professional translation engine. Output ONLY the translated word — no explanation, no labels.

### INPUT
Translate this {source_lang} word to {target_lang}: {input}

### OUTPUT
{target_lang} word:"""

    full_prompt = ChatPromptTemplate.from_template(full_template)
    simple_prompt = ChatPromptTemplate.from_template(simple_template)

    return (
        full_prompt | llm | StrOutputParser(),
        simple_prompt | llm | StrOutputParser(),
    )


# =========================
# ENGINE
# =========================
class OllamaEngine:
    def __init__(self, config=None):
        self.chain, self.simple_chain = get_chain()

    # -------------------------
    # LANGUAGE DETECTION
    # -------------------------
    def _detect_langs(self, text: str, direction: str | None):
        if direction and "->" in direction:
            src, tgt = direction.split("->")
            src, tgt = src.strip(), tgt.strip()
        else:
            src = "vi" if VI_PATTERN.search(text) else "en"
            tgt = "vi" if src == "en" else "en"

        label = {
            "en": "English",
            "vi": "Vietnamese"
        }

        return label.get(src, src), label.get(tgt, tgt)

    # -------------------------
    # KG + GLOSSARY MERGE
    # -------------------------
    def _build_kg_block(self, kg_terms: dict | None) -> str:
        merged = dict(STATIC_GLOSSARY)

        if kg_terms:
            merged.update(kg_terms)

        return "\n".join(
            f"- {k} → {v}"
            for k, v in merged.items()
        )

    # -------------------------
    # GLOSSARY LOOKUP
    # -------------------------
    def _lookup_glossary(
        self,
        text_lower: str,
        kg_terms: dict | None
    ) -> str | None:
        merged = dict(STATIC_GLOSSARY)
        if kg_terms:
            merged.update(kg_terms)

        # Chiều thuận: en→vi
        forward = {k.lower(): v for k, v in merged.items()}
        if text_lower in forward:
            return forward[text_lower]

        # Chiều ngược: vi→en
        reverse = {v.lower(): k for k, v in merged.items()}
        if text_lower in reverse:
            return reverse[text_lower]

        return None

    # -------------------------
    # POST PROCESS
    # -------------------------
    def _postprocess(
        self,
        raw: str,
        fallback: str
    ) -> str:

        result = raw.strip()

        result = re.sub(
            r"(?i)^(translation:|output:|target:|vietnamese translation:|english translation:|word:)\s*",
            "",
            result,
        )

        result = result.split("\n")[0].strip()

        # Fix 1: loại bỏ CJK + punctuation
        result = re.sub(
            r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+",
            "",
            result
        ).strip()

        # Fix 2: guard hallucination
        if len(result) < 1 or not re.search(
            r'[a-zA-ZÀ-ỹ]',
            result
        ):
            return fallback.strip()

        # Fix 3: viết hoa chữ đầu
        result = (
            result[0].upper() + result[1:]
            if result else result
        )

        return result

    # -------------------------
    # MAIN TRANSLATE
    # -------------------------
    def translate(
        self,
        text: str,
        rag_context: str | None = None,
        kg_terms: dict | None = None,
        direction: str | None = None,
        **kwargs,
    ) -> str:

        source_lang, target_lang = self._detect_langs(
            text,
            direction
        )

        text = text.strip()
        text_lower = text.lower()

        is_single_word = len(text.split()) <= 2

        # -------------------------
        # TIỀN XỬ LÝ — normalize input từ đơn
        # "dog" → "Dog", "DOG" → "Dog", "Dog" → "Dog"
        # -------------------------
        if is_single_word:
            text = (
                text[0].upper() + text[1:].lower()
                if text else text
            )

        # -------------------------
        # GLOSSARY SHORTCUT
        # (từ đơn có trong glossary → trả về luôn)
        # -------------------------
        if is_single_word:
            glossary_hit = self._lookup_glossary(
                text_lower,
                kg_terms
            )

            if glossary_hit:
                print(
                    f"[DEBUG GLOSSARY SHORTCUT] "
                    f"'{text}' → '{glossary_hit}'"
                )
                return glossary_hit

        # -------------------------
        # KG SHORTCUT
        # -------------------------
        if kg_terms:
            normalized = {
                k.lower(): v
                for k, v in kg_terms.items()
            }

            if text_lower in normalized:
                direct = normalized[text_lower]

                print(
                    f"[DEBUG KG SHORTCUT] "
                    f"'{text}' → '{direct}'"
                )

                return direct

        try:

            # -------------------------
            # TỪ ĐƠN KHÔNG CÓ TRONG GLOSSARY
            # → simple chain
            # -------------------------
            if is_single_word:

                print(
                    f"[DEBUG SIMPLE CHAIN] "
                    f"'{text}' không có trong glossary "
                    f"→ dùng simple template"
                )

                raw_output = self.simple_chain.invoke({
                    "input": text,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                })

            else:

                # -------------------------
                # CÂU DÀI → full chain
                # với glossary + examples
                # -------------------------
                kg_block = self._build_kg_block(
                    kg_terms
                )

                examples = (
                    rag_context
                    if rag_context else "None"
                )

                raw_output = self.chain.invoke({
                    "input": text,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "glossary": kg_block,
                    "examples": examples,
                })

            return self._postprocess(
                raw_output,
                fallback=text
            )

        except Exception as e:
            return f"Error: {e}"
