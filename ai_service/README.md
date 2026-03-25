# AI Service — TV2 (AI Engineer)

> **Người phụ trách:** TV2  
> **Stack:** Python 3.11 · FastAPI · HuggingFace MarianMT · LangChain · ChromaDB · Neo4j  
> **Port:** `localhost:8000`

---

## 📁 Cấu trúc thư mục

```
ai_service/
├── api/
│   ├── __init__.py
│   ├── routes/
│   │   ├── translate.py      ← POST /translate, GET /translate/{id}
│   │   ├── terms.py          ← GET /terms/lookup, POST /terms/normalize
│   │   └── health.py         ← GET /health
│   └── deps.py               ← JWT verify, DB session
│
├── models/
│   ├── marianmt_engine.py    ← Load model, translate(text) → str
│   ├── model_config.py       ← Model path, device (cpu/cuda), batch size
│   └── Helsinki-NLP/         ← Thư mục chứa model weights (KHÔNG commit lên git)
│
├── rag/
│   ├── pipeline.py           ← RAGPipeline class: retrieve() + augment()
│   ├── embeddings.py         ← SentenceTransformer encode()
│   ├── vector_store.py       ← ChromaDB/FAISS init, index(), search()
│   └── indexer.py            ← Script chạy 1 lần để index corpus vào vector store
│
├── kg/
│   ├── query_service.py      ← KGQueryService: lookup_term(), normalize()
│   ├── neo4j_client.py       ← Driver, Cypher queries
│   └── cypher_queries.py     ← Các query Cypher dùng chung
│
├── nlp/
│   ├── preprocessor.py       ← Tách câu, tokenize, làm sạch văn bản
│   └── postprocessor.py      ← Ghép câu, format output, handle PDF layout
│
├── tasks/
│   ├── celery_app.py         ← Celery config + RabbitMQ broker
│   └── translate_task.py     ← @celery_app.task: async translation job
│
├── schemas/
│   ├── translate.py          ← Pydantic models: TranslateRequest, TranslateResponse
│   └── term.py               ← TermLookupRequest, TermResponse
│
├── tests/
│   ├── test_marianmt.py      ← Unit test: translate("Hello") → str không rỗng
│   ├── test_rag.py           ← Unit test: retrieve() trả top-k > 0
│   ├── test_kg.py            ← Unit test: lookup_term("RAG") → "Tạo sinh tăng cường"
│   ├── test_api.py           ← Integration test: POST /translate → 200
│   └── conftest.py           ← Fixtures: mock DB, mock model
│
├── docs/
│   ├── postman_collection.json   ← Import vào Postman để test API
│   └── API_SPEC.md               ← Mô tả chi tiết từng endpoint
│
├── scripts/
│   ├── download_model.py     ← Tải MarianMT về models/ (chạy 1 lần)
│   ├── index_corpus.py       ← Index corpus vào ChromaDB (chạy sau khi có corpus)
│   └── eval_bleu.py          ← Tính BLEU trên test set, in report
│
├── main.py                   ← FastAPI app, include routers
├── requirements.txt
├── Dockerfile
├── alembic.ini
└── README.md                 ← File này
```

---

## ⚙️ Cài đặt môi trường

```bash
cd ai_service

# Tạo virtual env
python3 -m venv venv
source venv/bin/activate

# Cài dependencies
pip install -r requirements.txt

# Tải MarianMT model (chạy 1 lần, ~300MB)
python scripts/download_model.py
```

---

## 🚀 Chạy service

```bash
# Development (reload tự động)
uvicorn main:app --reload --port 8000

# Hoặc qua Docker
docker compose up ai_service

# Kiểm tra
curl http://localhost:8000/health
# → {"status": "ok", "model": "Helsinki-NLP/opus-mt-en-vi", "device": "cpu"}
```

---

## 📡 API Endpoints — Interface Contract với TV3

TV3 sẽ gọi các endpoint này. **Không được thay đổi request/response format sau khi bàn giao (Tuần 8).**

### `POST /translate`
```json
// Request
{
  "file_b64": "<base64 encoded PDF/DOCX/TXT>",
  "file_type": "pdf",         // "pdf" | "docx" | "txt"
  "domain": "computer_science" // "biology" | "physics" | "chemistry" | "general"
}

// Response 202 Accepted
{
  "job_id": "uuid-xxxx",
  "status": "pending",
  "estimated_seconds": 30
}
```

### `GET /translate/{job_id}`
```json
// Response 200 OK (khi xong)
{
  "job_id": "uuid-xxxx",
  "status": "completed",  // "pending" | "processing" | "completed" | "failed"
  "result": {
    "segments": [
      {
        "source": "Machine learning is a subset of AI.",
        "target": "Học máy là một tập hợp con của AI.",
        "confidence": 0.87,
        "terms_normalized": {
          "Machine learning": "Học máy",
          "AI": "Trí tuệ nhân tạo"
        }
      }
    ],
    "bleu_score": 38.2,
    "word_count": 1250,
    "processing_time_ms": 4200
  }
}
```

### `GET /terms/lookup?q=RAG&domain=computer_science`
```json
// Response 200 OK
{
  "term_en": "RAG",
  "term_vi": "Tạo sinh tăng cường",
  "definition_vi": "Kỹ thuật kết hợp truy xuất thông tin với mô hình ngôn ngữ...",
  "domain": "computer_science",
  "related_terms": ["LLM", "Embedding", "Vector Database"]
}
```

---

## 🧪 Chạy Tests

```bash
# Chạy tất cả unit tests (không cần Docker)
pytest tests/ -v --ignore=tests/test_api.py

# Chạy integration tests (cần Docker đang chạy)
pytest tests/test_api.py -v

# Đánh giá BLEU (cần corpus test từ TV4)
python scripts/eval_bleu.py --test-file ../data_pipeline/corpus/test.tsv
```

**Tiêu chuẩn PASS:**
- `test_marianmt.py`: translate() trả string không rỗng trong < 5s
- `test_rag.py`: retrieve() trả ≥ 1 kết quả với similarity > 0.5
- `test_kg.py`: lookup_term("Neural Network") → "Mạng nơ-ron" (exact match)
- `test_api.py`: POST /translate → 202, GET /translate/{id} → 200 với result

---

## 📋 Checklist bàn giao cho TV3 (Tuần 8)

```
[ ] Tất cả tests PASS: pytest tests/ -v
[ ] BLEU score >= 30 trên corpus/test.tsv
[ ] API chạy được: curl localhost:8000/health → OK
[ ] openapi.json export: curl localhost:8000/openapi.json > docs/openapi.json
[ ] Postman collection đã cập nhật: docs/postman_collection.json
[ ] docs/API_SPEC.md đã viết đầy đủ 3 endpoint
[ ] PR "feat: complete AI service handoff" → TV1 approve → merge
```

---

## ⚠️ Lưu ý quan trọng

- **KHÔNG commit** thư mục `models/Helsinki-NLP/` (đã add vào `.gitignore`)
- **KHÔNG commit** file `.env` chứa credentials
- Mỗi thay đổi schema Pydantic **phải thông báo TV3 trước**
- Nếu thêm endpoint mới sau Tuần 8, tạo issue `[TV2] New endpoint: /xxx` và assign TV3
