import re
from rag.vector_store import get_vectorstore


def detect_language(text: str):
    vi_pattern = r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]"
    if re.search(vi_pattern, text.lower()):
        return "vi"
    return "en"


def is_short_query(text: str):
    return len(text.strip().split()) <= 1


def preprocess_query(query: str):
    query = query.lower().strip()
    query = re.sub(r'[^\w\s]', '', query, flags=re.UNICODE)
    return " ".join(query.split()[:15])


def retrieve_docs(query: str, db_dir):
    if is_short_query(query):
        return []

    clean_query = preprocess_query(query)
    vectorstore = get_vectorstore(db_dir)

    docs_scores = vectorstore.similarity_search_with_score(clean_query, k=4)

    if not docs_scores:
        return []

    valid_results = [
        (doc, score)
        for doc, score in docs_scores
        if score < 0.6
    ]

    return valid_results[:2]


def build_rag_examples(query: str, db_dir):
    results = retrieve_docs(query, db_dir)

    if not results:
        return ""

    query_lang = detect_language(query)
    examples = []

    for i, (doc, score) in enumerate(results, start=1):
        print(f"[DEBUG RAG] score={score:.4f}")

        vi_val = doc.metadata.get("vi", "")
        en_val = doc.metadata.get("en", "")

        if query_lang == "vi":
            source = vi_val
            target = en_val
        else:
            source = en_val
            target = vi_val

        examples.append(
            f"Example {i}:\nSource: {source}\nTarget: {target}"
        )

    return "\n\n".join(examples)