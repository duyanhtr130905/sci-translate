# SCI-Translate 🔬🌐
> Hệ thống Dịch Thuật Chuyên Sâu Tài Liệu Khoa Học Anh-Việt  
> Môn: Data Mining | Nhóm: 4 người | Trường ĐHKHTN - ĐHQGHN

[![CI](https://github.com/your-org/sci-translate/actions/workflows/ci.yml/badge.svg)](...)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)](...)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 👥 Thành viên & phân công

| Thành viên | Vị trí | Phân hệ | Branch prefix |
|---|---|---|---|
| [TV1 - Họ tên] | Leader / BA Lead | BA & QA/QC + Tài liệu | `docs/`, `test/` |
| [TV2 - Họ tên] | AI Engineer | AI Module | `feature/ai-*` |
| [TV3 - Họ tên] | Web & Mobile Dev | CMS / Platforms / BI | `feature/web-*`, `feature/mobile-*` |
| [TV4 - Họ tên] | Data Engineer / QA | Dữ liệu | `feature/data-*` |

---

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND LAYER                        │
│   React Web App (3000)    Mobile App (Expo/RN)          │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP / REST
┌──────────────────────▼──────────────────────────────────┐
│              API GATEWAY — Drupal 10 (:80)               │
│              JWT Auth + JSON:API + REST                  │
└────────┬──────────────────────────┬─────────────────────┘
         │                          │
┌────────▼────────┐    ┌────────────▼────────────────────┐
│  AI SERVICE     │    │     ANALYTICS — Superset (:8088) │
│  FastAPI (:8000)│    │     ETL → Data Warehouse         │
│  MarianMT (local│    └─────────────────────────────────┘
│  RAG + KG       │
└────────┬────────┘
         │
┌────────▼──────────────────────────────────────────────┐
│                   DATA LAYER                           │
│  PostgreSQL(:5432)  Neo4j(:7474)  ChromaDB(:8001)     │
│  Redis(:6379)       RabbitMQ(:5672)                   │
└───────────────────────────────────────────────────────┘
```

---

## 🚀 Chạy nhanh (Development)

```bash
# 1. Clone repo
git clone https://github.com/your-org/sci-translate.git
cd sci-translate

# 2. Copy env file và điền thông tin
cp .env.example .env

# 3. Khởi động toàn bộ hệ thống (TV3 phụ trách file này)
docker compose up -d

# 4. Kiểm tra các service đang chạy
docker compose ps

# 5. Chạy migration DB
docker compose exec ai_service alembic upgrade head

# 6. Seed dữ liệu ban đầu (corpus nhỏ + KG)
docker compose exec ai_service python scripts/seed_data.py
```

**Truy cập:**
- Web App: http://localhost:3000
- AI API docs: http://localhost:8000/docs
- Drupal CMS: http://localhost:80
- Superset BI: http://localhost:8088
- Neo4j Browser: http://localhost:7474

---

## 📦 Cấu trúc thư mục

```
sci-translate/
├── ai_service/          ← TV2 sở hữu
├── data_pipeline/       ← TV4 sở hữu
├── cms/                 ← TV3 sở hữu (Drupal)
├── frontend/
│   ├── web/             ← TV3 sở hữu
│   └── mobile/          ← TV3 sở hữu
├── analytics/           ← TV3 sở hữu (Superset)
├── database/            ← TV4 sở hữu (schema + seed)
├── tests/
│   ├── e2e/             ← TV1 sở hữu
│   └── integration/     ← TV1 sở hữu
├── docs/                ← TV1 sở hữu
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── workflows/       ← CI/CD
├── docker-compose.yml   ← TV3 sở hữu
├── .env.example
└── README.md
```

---

## 🔗 Luồng bàn giao (Interface Contract)

### Bàn giao 1: TV4 → TV2 (Tuần 6)

TV4 bàn giao cho TV2 theo checklist:

```
[ ] corpus/train.tsv       — 50K+ cặp câu, UTF-8, tab-separated
[ ] corpus/test.tsv        — 5K cặp câu test (không dùng để train)
[ ] DB schema đã migrate   — docker compose exec ai_service alembic upgrade head
[ ] Neo4j KG seed          — 500+ nodes thuật ngữ đã import
[ ] File CONTRACT_V1.md    — mô tả format data chi tiết
```

**TV2 xác nhận bàn giao bằng cách:** Chạy `pytest data_pipeline/tests/ -v` → tất cả PASS, comment vào PR #handoff-1.

---

### Bàn giao 2: TV2 → TV3 (Tuần 8)

TV2 bàn giao cho TV3 theo checklist:

```
[ ] POST /translate        — nhận file, trả JSON song ngữ
[ ] GET  /translate/{id}   — lấy kết quả
[ ] GET  /terms/lookup     — tra cứu thuật ngữ KG
[ ] File openapi.json      — export từ FastAPI /openapi.json
[ ] Postman collection     — ai_service/docs/postman_collection.json
[ ] BLEU >= 30 trên test set
```

**TV3 xác nhận bàn giao bằng cách:** Chạy `pytest ai_service/tests/ -v` → tất cả PASS, comment vào PR #handoff-2.

---

## 🧪 Chạy Tests

```bash
# Unit tests từng module
pytest data_pipeline/tests/ -v          # TV4 chạy
pytest ai_service/tests/ -v             # TV2 chạy

# Integration tests (chạy sau khi docker compose up)
pytest tests/integration/ -v            # TV1 chạy sau W9

# End-to-end tests
pytest tests/e2e/ -v                    # TV1 chạy sau W10
```

---

## 🌿 Git Workflow

```bash
# Tạo branch mới
git checkout -b feature/ai-rag-pipeline   # TV2
git checkout -b feature/data-etl          # TV4
git checkout -b feature/web-translate-ui  # TV3
git checkout -b docs/usecase-update       # TV1

# Commit format
git commit -m "[TV2] feat: add RAG cosine similarity search"
git commit -m "[TV4] fix: handle empty corpus lines in ETL"
git commit -m "[TV3] feat: add bilingual display component"

# Push và tạo PR
git push origin feature/ai-rag-pipeline
# → Tạo PR trên GitHub, assign reviewer, chờ approve
```

**Quy tắc merge:**
- `main` branch: protected, chỉ merge qua PR
- Cần ít nhất 1 người approve
- CI phải PASS trước khi merge

---

## 📋 Tài liệu thêm

- [Tài liệu PTTK đầy đủ](docs/PTTK_DataMining.pdf)
- [TV2: AI Service README](ai_service/README.md)
- [TV4: Data Pipeline README](data_pipeline/README.md)
- [TV3: Frontend README](frontend/web/README.md)
- [TV3: CMS README](cms/README.md)
- [TV1: Test Strategy](docs/TEST_STRATEGY.md)
- [Contract: TV4 → TV2](docs/CONTRACT_DATA_TO_AI.md)
- [Contract: TV2 → TV3](docs/CONTRACT_AI_TO_WEB.md)
