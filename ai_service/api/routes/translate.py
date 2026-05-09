import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fastapi.concurrency import run_in_threadpool

from models.ollama_engine import OllamaEngine
from nlp.preprocessor import preprocessor
from nlp.postprocessor import postprocessor
from rag.pipeline import build_rag_examples
from kg.query_service import KGQueryService

router = APIRouter(prefix="/translate", tags=["translate"])


class TranslateRequest(BaseModel):
    text: str
    source_lang: str | None = None
    target_lang: str | None = None


class TranslateResponse(BaseModel):
    original_text: str
    translated_text: str
    source_lang: str
    target_lang: str


VECTORSTORE_DIR = os.getenv("VECTOR_DB_PATH", "/app/vectorstore")

engine = OllamaEngine()
kg_service = KGQueryService()


@router.post("/", response_model=TranslateResponse)
async def translate_text(payload: TranslateRequest):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty input")

    # 1. Detect language
    detected_lang = preprocessor.detect_language(text)
    source_lang = payload.source_lang or detected_lang
    target_lang = payload.target_lang or ("vi" if source_lang == "en" else "en")
    direction = f"{source_lang}->{target_lang}"

    # 2. RAG
    examples = await run_in_threadpool(build_rag_examples, text, VECTORSTORE_DIR)
    print(f"[DEBUG RAG] Examples found: {examples}")

    # 3. KG
    kg_terms = await run_in_threadpool(
        lambda: kg_service.get_context_for_translation(text)
    )
    print(f"[DEBUG KG] Terms found: {kg_terms}")

    # 4. Translate
    result = await run_in_threadpool(
        lambda: engine.translate(
            text,
            rag_context=examples,
            kg_terms=kg_terms,
            direction=direction,
        )
    )
    print(f"[DEBUG ENGINE] Output: {result}")

    # 5. Postprocess
    final = postprocessor.clean_output(result)

    return TranslateResponse(
        original_text=text,
        translated_text=final,
        source_lang=source_lang,
        target_lang=target_lang,
    )