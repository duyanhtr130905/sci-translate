# AI Service — TV2 (AI Engineer)

> **Người phụ trách:** TV2  
> **Stack:** Python 3.11 · FastAPI · Ollama (LLM cục bộ) · LangChain · ChromaDB · Neo4j  
> **Port:** `localhost:8000`  
> **Ollama:** `localhost:11434`

---

## 🔄 Changelog so với bản cũ (MarianMT → Ollama)

| Hạng mục | Bản cũ (MarianMT) | Bản mới (Ollama) |
|---|---|---|
| **Translation engine** | HuggingFace MarianMT (NMT) | Ollama LLM cục bộ (Gemma 2 / Qwen 2.5 / Mistral) |
| **Model storage** | `models/Helsinki-NLP/` (~300MB weights) | Ollama daemon tự quản lý (`~/.ollama/models/`) |
| **Model config** | `models/model_config.py` (device, batch_size) | `models/ollama_config.py` (endpoint, model name, temperature, system prompt) |
| **Engine file** | `models/marianmt_engine.py` | `models/ollama_engine.py` |
| **Download script** | `scripts/download_model.py` (Python) | `scripts/pull_model.sh` (Shell — gọi `ollama pull`) |
| **Unit test engine** | `tests/test_marianmt.py` | `tests/test_ollama.py` |
| **Dependencies bỏ** | — | `transformers`, `torch`, `sentencepiece`, `sacremoses` |
| **Dependencies thêm** | — | `ollama`, `langchain-ollama`, `httpx` |
| **RAG pipeline** | Giữ nguyên | Giữ nguyên |
| **Knowledge Graph** | Giữ nguyên | Giữ nguyên |
| **NLP pre/post** | Giữ nguyên | Giữ nguyên |
| **API contract** | Giữ nguyên | **Giữ nguyên 100%** — TV3 không bị ảnh hưởng |

---

## 📁 Cấu trúc thư mục

```
ai_service/
├── api/
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── translate.py      ← POST /translate, GET /translate/{id}
│   │   ├── terms.py          ← GET /terms/lookup, POST /terms/normalize
│   │   └── health.py         ← GET /health (trả info Ollama model)
│   └── deps.py               ← JWT verify, DB session
│
├── models/
│   ├── __init__.py
│   ├── ollama_engine.py      ← OllamaEngine: translate(text, context) → str
│   └── ollama_config.py      ← Ollama endpoint, model name, temperature, system prompt
│
├── rag/
│   ├── __init__.py
│   ├── pipeline.py           ← RAGPipeline class: retrieve() + augment()
│   ├── embeddings.py         ← SentenceTransformer encode()
│   ├── vector_store.py       ← ChromaDB/FAISS init, index(), search()
│   └── indexer.py            ← Script chạy 1 lần để index corpus vào vector store
│
├── kg/
│   ├── __init__.py
│   ├── query_service.py      ← KGQueryService: lookup_term(), normalize()
│   ├── neo4j_client.py       ← Driver, Cypher queries
│   └── cypher_queries.py     ← Các query Cypher dùng chung
│
├── nlp/
│   ├── __init__.py
│   ├── preprocessor.py       ← Tách câu, tokenize, làm sạch văn bản
│   └── postprocessor.py      ← Ghép câu, format output, handle PDF layout
│
├── tasks/
│   ├── __init__.py
│   ├── celery_app.py         ← Celery config + RabbitMQ broker
│   └── translate_task.py     ← @celery_app.task: async translation job (gọi Ollama)
│
├── schemas/
│   ├── __init__.py
│   ├── translate.py          ← Pydantic models: TranslateRequest, TranslateResponse
│   └── term.py               ← TermLookupRequest, TermResponse
│
├── tests/
│   ├── test_ollama.py        ← Unit test: OllamaEngine.translate("Hello") → str không rỗng
│   ├── test_rag.py           ← Unit test: retrieve() trả top-k > 0
│   ├── test_kg.py            ← Unit test: lookup_term("RAG") → "Tạo sinh tăng cường"
│   ├── test_api.py           ← Integration test: POST /translate → 202
│   └── conftest.py           ← Fixtures: mock Ollama client, mock DB
│
├── docs/
│   ├── postman_collection.json   ← Import vào Postman để test API
│   └── API_SPEC.md               ← Mô tả chi tiết từng endpoint
│
├── scripts/
│   ├── pull_model.sh         ← Tải model Ollama (chạy 1 lần): ollama pull gemma2
│   ├── index_corpus.py       ← Index corpus vào ChromaDB (chạy sau khi có corpus)
│   └── eval_bleu.py          ← Tính BLEU trên test set, in report
│
├── main.py                   ← FastAPI app, include routers
├── requirements.txt
├── Dockerfile
├── .env.example              ← Biến môi trường mẫu (Ollama, Neo4j, ChromaDB...)
├── alembic.ini
└── README.md                 ← File này
```

---

## ⚙️ Cài đặt môi trường

### Bước 1 — Cài Ollama (chạy 1 lần)

```bash
# ── Linux / WSL ──
curl -fsSL https://ollama.ai/install.sh | sh

# ── macOS ──
brew install ollama

# ── Windows ──
# Tải installer từ https://ollama.com/download/windows

# Kiểm tra cài đặt
ollama --version
```

### Bước 2 — Pull model dịch thuật

```bash
# Khuyến nghị: Gemma 2 9B (tốt cho dịch EN→VI, ~5.4GB)
ollama pull gemma2

# Hoặc alternatives:
# ollama pull qwen2.5        # Qwen 2.5 (mạnh multilingual)
# ollama pull mistral         # Mistral 7B (nhẹ, nhanh)

# Hoặc chạy script:
bash scripts/pull_model.sh
```

### Bước 3 — Cài Python dependencies

```bash
cd ai_service

# Tạo virtual env
python3 -m venv venv
source venv/bin/activate      # Linux/macOS
# venv\Scripts\activate       # Windows

# Cài dependencies
pip install -r requirements.txt
```

### Bước 4 — Cấu hình biến môi trường

```bash
cp .env.example .env
# Sửa .env theo môi trường thực
```

**Biến môi trường Ollama quan trọng:**
```env
# ── Ollama ──
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma2
OLLAMA_TEMPERATURE=0.3
OLLAMA_NUM_CTX=4096
OLLAMA_TIMEOUT=120
```

---

## 🚀 Chạy service

```bash
# 1. Đảm bảo Ollama daemon đang chạy
ollama serve                  # Nếu chưa chạy (mặc định port 11434)

# 2. Kiểm tra model đã pull chưa
ollama list                   # Phải thấy "gemma2" hoặc model đã chọn

# 3. Chạy AI service (development, reload tự động)
uvicorn main:app --reload --port 8000

# 4. Hoặc qua Docker
docker compose up ai_service

# 5. Kiểm tra health
curl http://localhost:8000/health
# → {"status": "ok", "engine": "ollama", "model": "gemma2", "ollama_url": "http://localhost:11434"}
```

---

## 🧠 Luồng dịch thuật (Translation Pipeline)

```
Input (PDF/DOCX/TXT)
       │
       ▼
┌──────────────┐
│  Preprocessor │ ← nlp/preprocessor.py: tách câu, làm sạch
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌───────────────┐
│  RAG Retrieve │────▶│ ChromaDB      │ ← Lấy context tương tự từ corpus
└──────┬───────┘     └───────────────┘
       │ context
       ▼
┌──────────────┐     ┌───────────────┐
│  KG Lookup   │────▶│ Neo4j         │ ← Tra thuật ngữ chuyên ngành
└──────┬───────┘     └───────────────┘
       │ terms
       ▼
┌──────────────────────────────────────┐
│  Ollama LLM (Gemma 2 / Qwen 2.5)    │
│                                      │
│  System Prompt:                      │
│  "Bạn là chuyên gia dịch tài liệu   │
│   khoa học EN→VI. Sử dụng thuật ngữ  │
│   chuyên ngành đã cho..."            │
│                                      │
│  User Prompt:                        │
│  "Dịch câu sau sang tiếng Việt.      │
│   Context: {rag_context}             │
│   Thuật ngữ: {kg_terms}             │
│   Câu: {source_sentence}"           │
└──────┬───────────────────────────────┘
       │ translated text
       ▼
┌──────────────┐
│ Postprocessor │ ← nlp/postprocessor.py: ghép câu, format
└──────┬───────┘
       │
       ▼
Output (JSON segments)
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

## 📦 Dependencies (`requirements.txt`)

### Core Framework
```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
pydantic>=2.6.0
python-multipart>=0.0.9
python-jose[cryptography]>=3.3.0
```

### Ollama (Translation Engine) — MỚI
```
ollama>=0.4.0
langchain-ollama>=0.3.0
httpx>=0.27.0
```

### RAG Pipeline
```
langchain>=0.3.0
langchain-community>=0.3.0
chromadb>=0.5.0
sentence-transformers>=3.0.0
```

### Knowledge Graph
```
neo4j>=5.20.0
```

### Task Queue
```
celery[redis]>=5.4.0
redis>=5.0.0
```

### Database
```
sqlalchemy>=2.0.0
alembic>=1.13.0
psycopg2-binary>=2.9.0
```

### Testing & Evaluation
```
pytest>=8.0.0
pytest-asyncio>=0.23.0
sacrebleu>=2.4.0
```

### So sánh với bản cũ

| Bỏ (MarianMT) | Thêm (Ollama) |
|---|---|
| `transformers` | `ollama>=0.4.0` |
| `torch` (~2GB) | `langchain-ollama>=0.3.0` |
| `sentencepiece` | `httpx>=0.27.0` |
| `sacremoses` | — |

> ⚡ **Lợi ích:** Bỏ `torch` giảm ~2GB dung lượng venv. Ollama model được quản lý riêng bởi Ollama daemon.

---

## 🧪 Chạy Tests

```bash
# Chạy tất cả unit tests (cần Ollama đang chạy)
pytest tests/ -v --ignore=tests/test_api.py

# Chạy integration tests (cần Docker đang chạy)
pytest tests/test_api.py -v

# Đánh giá BLEU (cần corpus test từ TV4)
python scripts/eval_bleu.py --test-file ../data_pipeline/corpus/test.tsv
```

**Tiêu chuẩn PASS:**
- `test_ollama.py`: `OllamaEngine.translate()` trả string không rỗng trong < 30s (LLM chậm hơn NMT)
- `test_rag.py`: `retrieve()` trả ≥ 1 kết quả với similarity > 0.5
- `test_kg.py`: `lookup_term("Neural Network")` → `"Mạng nơ-ron"` (exact match)
- `test_api.py`: `POST /translate` → 202, `GET /translate/{id}` → 200 với result

---

## 📋 Checklist bàn giao cho TV3 (Tuần 8)

```
[ ] Ollama daemon chạy được: ollama list → hiện model
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

- **Ollama phải chạy trước** khi start AI service. Nếu Ollama daemon chưa chạy → service sẽ báo lỗi tại `/health`
- **KHÔNG commit** file `.env` chứa credentials
- **Model Ollama không nằm trong repo** — mỗi dev cần tự `ollama pull gemma2` (hoặc chạy `scripts/pull_model.sh`)
- Mỗi thay đổi schema Pydantic **phải thông báo TV3 trước**
- Nếu thêm endpoint mới sau Tuần 8, tạo issue `[TV2] New endpoint: /xxx` và assign TV3
- **Timeout:** LLM generation chậm hơn MarianMT NMT. Đặt `OLLAMA_TIMEOUT=120` (giây) để tránh timeout khi dịch đoạn dài
- **RAM khuyến nghị:** ≥ 16GB RAM cho model 7B–9B. Nếu máy yếu, dùng model nhỏ hơn (`ollama pull gemma2:2b`)
- **GPU (tuỳ chọn):** Ollama tự detect NVIDIA GPU. Nếu có GPU → tốc độ nhanh hơn ~5-10x
