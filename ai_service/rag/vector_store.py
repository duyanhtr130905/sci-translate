import os
import shutil
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from rag.embeddings import get_embeddings

_vectorstore_cache: dict = {}

def get_vectorstore(db_dir: str):
    global _vectorstore_cache
    if db_dir not in _vectorstore_cache:
        if not os.path.exists(db_dir):
            raise FileNotFoundError(f"Không tìm thấy vector DB: {db_dir}")
        _vectorstore_cache[db_dir] = Chroma(
            persist_directory=db_dir,
            embedding_function=get_embeddings()
        )
    return _vectorstore_cache[db_dir]

def build_vectorstore(data: list[dict], db_dir: str):
    global _vectorstore_cache

    print("--- [PROCESS] Building Dual-Language Vector DB ---")
    documents = []

    for item in data:
        vi_clean = item["vi"].replace("||", "").strip()
        en_clean = item["en"].replace("||", "").strip()

        if not vi_clean or not en_clean:   # skip incomplete pairs
            continue

        documents.append(Document(
            page_content=en_clean,
            metadata={"vi": vi_clean, "en": en_clean, "primary_lang": "en"}
        ))
        documents.append(Document(
            page_content=vi_clean,
            metadata={"vi": vi_clean, "en": en_clean, "primary_lang": "vi"}
        ))

    if os.path.exists(db_dir):
        shutil.rmtree(db_dir)

    # Invalidate cache so next get_vectorstore loads fresh from disk
    _vectorstore_cache.pop(db_dir, None)

    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=get_embeddings(),
        persist_directory=db_dir,
        collection_metadata={"hnsw:space": "cosine"}
    )

    print(f"--- [SUCCESS] {len(documents)} documents indexed to: {db_dir} ---")
    return vectorstore