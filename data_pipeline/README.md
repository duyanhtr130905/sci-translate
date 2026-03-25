# Data Pipeline — TV4 (Data Engineer / QA)

> **Người phụ trách:** TV4  
> **Stack:** Python 3.11 · Pandas · SQLAlchemy · Alembic · Neo4j · PostgreSQL  
> **Bàn giao cho TV2:** Tuần 6

---

## 📁 Cấu trúc thư mục

```
data_pipeline/
├── collectors/
│   ├── arxiv_collector.py      ← Thu thập abstracts từ arXiv API
│   ├── pubmed_collector.py     ← Thu thập từ PubMed (NCBI E-utilities)
│   ├── acl_collector.py        ← Thu thập từ ACL Anthology
│   └── base_collector.py      ← Base class: fetch(), save_raw()
│
├── etl/
│   ├── cleaner.py              ← Làm sạch văn bản: xóa HTML, normalize unicode
│   ├── aligner.py              ← Align cặp câu EN-VI, loại câu quá ngắn/dài
│   ├── deduplicator.py         ← Loại trùng lặp bằng hash
│   ├── splitter.py             ← Chia train/test (90/10)
│   └── loader.py               ← Load vào PostgreSQL (bảng translation_memory)
│
├── validators/
│   ├── schema_validator.py     ← Kiểm tra format TSV: 2 cột, UTF-8
│   ├── quality_validator.py    ← Kiểm tra: độ dài câu, language detection
│   └── stats_reporter.py      ← In báo cáo: tổng cặp, avg length, domain dist
│
├── kg/
│   ├── term_importer.py        ← Import thuật ngữ từ CSV vào Neo4j
│   ├── relation_builder.py     ← Tạo edges: synonym, hypernym, translation_of
│   └── seed_data/
│       ├── cs_terms.csv        ← 200+ thuật ngữ Computer Science
│       ├── nlp_terms.csv       ← 150+ thuật ngữ NLP/AI
│       ├── bio_terms.csv       ← 100+ thuật ngữ Biology
│       └── physics_terms.csv  ← 80+ thuật ngữ Physics
│
├── tests/
│   ├── test_etl.py             ← Unit test: cleaner, aligner, deduplicator
│   ├── test_validators.py      ← Unit test: schema check, quality check
│   ├── test_kg.py              ← Unit test: Neo4j node count >= 500
│   └── test_db.py              ← Integration test: PostgreSQL connection OK
│
├── scripts/
│   ├── run_full_pipeline.py    ← Chạy toàn bộ pipeline 1 lệnh
│   └── check_handoff.py        ← Tự kiểm tra checklist bàn giao → in Pass/Fail
│
├── corpus/                     ← OUTPUT — TV2 đọc từ đây
│   ├── train.tsv               ← 50K+ cặp câu (EN\tVI)
│   ├── test.tsv                ← 5K cặp câu test
│   └── .gitkeep
│
├── requirements.txt
├── Dockerfile
└── README.md                   ← File này
```

---

## ⚙️ Cài đặt

```bash
cd data_pipeline
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Kiểm tra kết nối DB (cần Docker đang chạy)
python -c "from etl.loader import check_connection; check_connection()"
```

---

## 🚀 Chạy pipeline

```bash
# Chạy toàn bộ (thu thập → làm sạch → load DB → seed KG)
python scripts/run_full_pipeline.py

# Hoặc từng bước
python collectors/arxiv_collector.py --domain cs.CL --max 20000
python collectors/pubmed_collector.py --domain NLP --max 15000

python etl/cleaner.py --input raw/ --output cleaned/
python etl/aligner.py --input cleaned/ --output aligned/
python etl/deduplicator.py --input aligned/ --output corpus/
python etl/splitter.py --input corpus/all.tsv --train corpus/train.tsv --test corpus/test.tsv
python etl/loader.py --file corpus/train.tsv

# Seed Knowledge Graph
python kg/term_importer.py --csv kg/seed_data/cs_terms.csv
python kg/term_importer.py --csv kg/seed_data/nlp_terms.csv
python kg/relation_builder.py
```

---

## 📋 Format bàn giao cho TV2

### File `corpus/train.tsv`
```
# Format: EN TAB VI (mỗi dòng 1 cặp câu)
Machine learning is a subset of AI.	Học máy là một tập hợp con của AI.
The model was trained on a large dataset.	Mô hình được huấn luyện trên tập dữ liệu lớn.
```

**Tiêu chuẩn chất lượng:**
- Encoding: UTF-8, không có BOM
- Số dòng: ≥ 50,000 (train), ≥ 5,000 (test)
- Độ dài câu: 5 ≤ token_count ≤ 100
- Không có dòng trùng lặp (hash-dedup)
- Language detection: source=EN, target=VI với confidence ≥ 0.9

### Neo4j Knowledge Graph
```cypher
// Kiểm tra sau khi seed
MATCH (t:Term) RETURN count(t) AS total_terms    // >= 500
MATCH ()-[r]->() RETURN count(r) AS total_edges  // >= 1000
MATCH (t:Term {term_en: "RAG"}) RETURN t         // phải tồn tại
```

### Database schema
```bash
# Kiểm tra migration đã chạy
docker compose exec ai_service alembic current
# Output phải là: head (tức là đã ở revision mới nhất)
```

---

## 🧪 Chạy Tests

```bash
# Unit tests (không cần Docker)
pytest tests/test_etl.py tests/test_validators.py -v

# Integration tests (cần Docker)
pytest tests/test_db.py tests/test_kg.py -v

# Tự kiểm tra checklist bàn giao
python scripts/check_handoff.py
# Output mong muốn:
# [PASS] corpus/train.tsv: 52,341 dòng
# [PASS] corpus/test.tsv:  5,234 dòng
# [PASS] PostgreSQL: kết nối OK, bảng translation_memory: 52,341 rows
# [PASS] Neo4j: 523 nodes, 1,247 edges
# [PASS] Language detection accuracy: 98.3%
# ✅ Sẵn sàng bàn giao cho TV2!
```

---

## 📋 Checklist bàn giao (Tuần 6)

```
[ ] python scripts/check_handoff.py → tất cả PASS
[ ] pytest tests/ -v → tất cả PASS
[ ] corpus/train.tsv: >= 50,000 dòng
[ ] corpus/test.tsv:  >= 5,000 dòng
[ ] Neo4j: >= 500 nodes, >= 1000 edges
[ ] DB migration: alembic current → head
[ ] docs/CONTRACT_DATA_TO_AI.md đã viết
[ ] Tạo issue "Handoff TV4→TV2 complete" và tag TV2
[ ] PR "feat: complete data pipeline" → TV1 approve → merge vào main
```

---

## 🧪 Vai trò QA/QC (Tuần 10-11)

Sau khi hệ thống AI chạy, TV4 thực hiện QA review:

```bash
# Tải 50 bản dịch từ hệ thống để review
curl http://localhost:8000/translate/batch-sample?n=50 > qa_samples.json

# Mở file review (TV4 điền thủ công)
# File: qa_review_log.xlsx (xem template trong docs/)
```

**Tiêu chí review mỗi bản dịch (thang điểm 1-5):**
- Độ chính xác ngữ nghĩa (40%)
- Chuẩn xác thuật ngữ (30%)
- Ngữ pháp tiếng Việt (15%)
- Tính tự nhiên / fluency (15%)

**Mục tiêu:** Human score trung bình ≥ 3.5/5 trên 50 bản dịch.

---

## ⚠️ Lưu ý

- **KHÔNG commit** thư mục `raw/` (dữ liệu thô, có thể lớn vài GB)
- File `corpus/train.tsv` và `corpus/test.tsv` được commit (đã gitignore `raw/`)
- Mọi thay đổi schema DB **phải tạo migration file mới** bằng Alembic
- Nếu thêm thuật ngữ mới vào KG sau Tuần 6, thông báo TV2 để re-index ChromaDB
