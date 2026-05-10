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


def get_chain():
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    params = get_ollama_params()

    llm = OllamaLLM(
    base_url=ollama_url,
    model=MODEL_AI,

    temperature=0.0,      
    top_k=1,              
    top_p=1.1,            
    repeat_penalty=1.0,   

    num_ctx=4096,
    num_gpu=params["num_gpu"],
    num_thread=params["num_thread"],

    stop=["### INPUT", "Source (", "---"],
)

    template = """### SYSTEM
You are a professional translation engine. Output ONLY the translation — no labels, no explanation, no punctuation changes.

### MANDATORY GLOSSARY (you MUST use these exact translations if the term appears in source):
{glossary}

### EXAMPLES (style reference only):
{examples}

### INPUT
Source ({source_lang}): {input}

### OUTPUT
{target_lang} translation (use MANDATORY GLOSSARY terms exactly):"""

    prompt = ChatPromptTemplate.from_template(template)
    return prompt | llm | StrOutputParser()


class OllamaEngine:
    def __init__(self, config=None):
        self.chain = get_chain()

    
    def _detect_langs(self, text: str, direction: str | None):
        if direction and "->" in direction:
            src, tgt = direction.split("->")
            src, tgt = src.strip(), tgt.strip()
        else:
            src = "vi" if VI_PATTERN.search(text) else "en"
            tgt = "vi" if src == "en" else "en"

        label = {"en": "English", "vi": "Vietnamese"}
        return label.get(src, src), label.get(tgt, tgt)

    
    def _build_kg_block(self, kg_terms: dict | None) -> str:
        merged = dict(STATIC_GLOSSARY)
        if kg_terms:
            merged.update(kg_terms)

        return "\n".join(f"- {k} → {v}" for k, v in merged.items())

    
    def _postprocess(self, raw: str, fallback: str) -> str:
        result = raw.strip()

        result = re.sub(
            r"(?i)^(translation:|output:|target:|vietnamese translation:|english translation:)\s*",
            "",
            result,
        )

        result = result.split("\n")[0].strip()

        result = re.sub(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+", "", result).strip()

        if len(result) < 2 or not re.search(r'[a-zA-ZÀ-ỹ]', result):
            return fallback.strip()

        return result

    
    def translate(
        self,
        text: str,
        rag_context: str | None = None,
        kg_terms: dict | None = None,
        direction: str | None = None,
        **kwargs,
    ) -> str:

        source_lang, target_lang = self._detect_langs(text, direction)
        kg_block = self._build_kg_block(kg_terms)
        examples = rag_context if rag_context else "None"

        text_lower = text.strip().lower()
        if kg_terms:
            normalized = {k.lower(): v for k, v in kg_terms.items()}
            if text_lower in normalized:
                direct = normalized[text_lower]
                print(f"[DEBUG KG SHORTCUT] '{text}' → '{direct}'")
                return direct

        try:
            raw_output = self.chain.invoke({
                "input": text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "glossary": kg_block,
                "examples": examples,
            })

            return self._postprocess(raw_output, fallback=raw_output)

        except Exception as e:
            return f"Error: {e}"