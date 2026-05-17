# Data Pipeline — TV4 (Data Engineer / QA)

> **Người phụ trách:** TV4  
> **Stack:** Python 3.11 · Scrapy · Pandas · SQLAlchemy · PostgreSQL · Neo4j  
> **Bàn giao cho TV2:** Tuần 6

---

## 📁 Cấu trúc thư mục

```text
data_pipeline/
├── collectors/
│   ├── arxiv_collector.py      ← Đọc dữ liệu câu EN/VI arXiv từ Google Drive public
│   ├── pubmed_collector.py     ← Đọc dữ liệu câu EN/VI PubMed từ Google Drive public
│   ├── acl_collector.py        ← Đọc dữ liệu câu EN/VI ACL từ Google Drive public
│   └── base_collector.py       ← Base class: fetch(), save_raw(), normalize_text()
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
│   └── stats_reporter.py       ← In báo cáo: tổng cặp, avg length, domain dist
│
├── kg/
│   ├── term_importer.py        ← Import thuật ngữ từ CSV vào Neo4j
│   ├── relation_builder.py     ← Tạo edges: synonym, hypernym, translation_of
│   └── seed_data/
│       ├── cs_terms.csv        ← 200+ thuật ngữ Computer Science
│       ├── nlp_terms.csv       ← 150+ thuật ngữ NLP/AI
│       ├── bio_terms.csv       ← 100+ thuật ngữ Biology
│       └── physics_terms.csv   ← 80+ thuật ngữ Physics
│
├── tests/
│   ├── test_etl.py             ← Unit test: cleaner, aligner, deduplicator
│   ├── test_validators.py      ← Unit test: schema check, quality check
│   ├── test_kg.py              ← Integration test: Neo4j node count >= 500
│   └── test_db.py              ← Integration test: PostgreSQL connection OK
│
├── scripts/
│   ├── run_full_pipeline.py    ← Chạy toàn bộ pipeline 1 lệnh
│   └── check_handoff.py        ← Tự kiểm tra checklist bàn giao → in Pass/Fail
│
├── raw/                        ← OUTPUT tạm thời từ collectors
├── cleaned/                    ← OUTPUT sau cleaner
├── aligned/                    ← OUTPUT sau aligner
├── deduplicated/               ← OUTPUT sau deduplicator
├── corpus/                     ← OUTPUT cuối cùng — TV2 đọc từ đây
│   ├── train.tsv               ← 50K+ cặp câu EN\tVI
│   ├── test.tsv                ← 5K+ cặp câu test
│   └── .gitkeep
│
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## ⚙️ Cài đặt môi trường Python

### PowerShell trên Windows

```powershell
cd data_pipeline
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Nếu PowerShell chặn activate script, chạy:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```


Cần set biến môi trường như sau trong PowerShell:

```powershell
$env:DATABASE_URL="postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/sci_translate"

$env:NEO4J_URI="bolt://localhost:7687"
$env:NEO4J_USER="neo4j"
$env:NEO4J_PASSWORD="N3o4jSci2026!"
```

> Lưu ý: các biến trên chỉ áp dụng cho phiên PowerShell hiện tại. Nếu đóng terminal, cần set lại.

Kiểm tra kết nối PostgreSQL:

```powershell
python etl\loader.py --check
```

Kiểm tra kết nối Neo4j bằng cách import thử seed data:

```powershell
python kg\term_importer.py --csv kg\seed_data\cs_terms.csv
```



## 🚀 Chạy pipeline

### Cách 1: chạy toàn bộ pipeline một lệnh

Nếu muốn chạy đầy đủ:

```powershell
python scripts\run_full_pipeline.py
```

Nếu muốn bỏ qua bước load DB và seed KG để test ETL trước:

```powershell
python scripts\run_full_pipeline.py --skip-db-load --skip-kg
```

Nếu đã có dữ liệu trong `raw/` và muốn bỏ qua collectors:

```powershell
python scripts\run_full_pipeline.py --skip-collectors --skip-db-load --skip-kg
```

---

## 🚀 Chạy pipeline từng bước

### 1. Thu thập dữ liệu từ collectors

Các collector hiện đọc dữ liệu câu EN/VI từ Google Drive public và xuất ra thư mục `raw/`.

Không truyền `max_results` để lấy tối đa số câu hiện có trong nguồn dữ liệu.

```powershell
python -m scrapy runspider collectors/arxiv_collector.py -a save_separate=true -a en_output_file=raw/arxiv_sentences_en.json -a vi_output_file=raw/arxiv_sentences_vi.json

python -m scrapy runspider collectors/pubmed_collector.py -a save_separate=true -a en_output_file=raw/pubmed_sentences_en.json -a vi_output_file=raw/pubmed_sentences_vi.json

python -m scrapy runspider collectors/acl_collector.py -a save_separate=true -a en_output_file=raw/acl_sentences_en.json -a vi_output_file=raw/acl_sentences_vi.json
```

Nếu chỉ muốn lấy thử 1000 câu để test nhanh, thêm:

```powershell
-a max_results=1000
```

Ví dụ:

```powershell
python -m scrapy runspider collectors/arxiv_collector.py -a save_separate=true -a max_results=1000 -a en_output_file=raw/arxiv_sentences_en.json -a vi_output_file=raw/arxiv_sentences_vi.json
```

---

### 2. Làm sạch dữ liệu

```powershell
python etl\cleaner.py --input raw\ --output cleaned\ --drop-empty
```

---

### 3. Align từng cặp EN–VI

```powershell
python etl\aligner.py --en cleaned/arxiv_sentences_en.json --vi cleaned/arxiv_sentences_vi.json --output aligned/arxiv_aligned.json

python etl\aligner.py --en cleaned/pubmed_sentences_en.json --vi cleaned/pubmed_sentences_vi.json --output aligned/pubmed_aligned.json

python etl\aligner.py --en cleaned/acl_sentences_en.json --vi cleaned/acl_sentences_vi.json --output aligned/acl_aligned.json
```

---

### 4. Loại trùng lặp

```powershell
python etl\deduplicator.py --input aligned --output deduplicated --mode bilingual --fields en vi --drop-empty --rename-suffix-from _aligned --rename-suffix-to _dedup
```

Kết quả dự kiến:

```text
deduplicated/
├── arxiv_dedup.json
├── pubmed_dedup.json
└── acl_dedup.json
```

---

### 5. Chia train/test 90/10

```powershell
python etl\splitter.py --input deduplicated --train corpus/train.tsv --test corpus/test.tsv --mode bilingual
```

Kết quả:

```text
corpus/
├── train.tsv
└── test.tsv
```

---

### 6. Kiểm tra và nạp dữ liệu vào PostgreSQL

Set env trước nếu chưa set:

```powershell
$env:DATABASE_URL="postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/sci_translate"
```

Kiểm tra kết nối:

```powershell
python etl\loader.py --check
```

Load file train:

```powershell
python etl\loader.py --file corpus/train.tsv
```

Nếu file TSV có header:

```powershell
python etl\loader.py --file corpus/train.tsv --has-header
```

---

### 7. Seed Knowledge Graph vào Neo4j

Set env trước nếu chưa set:

```powershell
$env:NEO4J_URI="bolt://localhost:7687"
$env:NEO4J_USER="neo4j"
$env:NEO4J_PASSWORD="N3o4jSci2026!"
```

Import thuật ngữ:

```powershell
python kg\term_importer.py --csv kg\seed_data\cs_terms.csv
python kg\term_importer.py --csv kg\seed_data\nlp_terms.csv
python kg\term_importer.py --csv kg\seed_data\bio_terms.csv
python kg\term_importer.py --csv kg\seed_data\physics_terms.csv
```

Tạo quan hệ:

```powershell
python kg\relation_builder.py
```

---

### 8. Kiểm tra chất lượng dữ liệu

Quality check:

```powershell
python validators\quality_validator.py --file corpus/train.tsv --min-confidence 0.9
python validators\quality_validator.py --file corpus/test.tsv --min-confidence 0.9
```

Schema check:

```powershell
python validators\schema_validator.py --file corpus/train.tsv
python validators\schema_validator.py --file corpus/test.tsv
```

Stats report:

```powershell
python validators\stats_reporter.py --file corpus/train.tsv
python validators\stats_reporter.py --file corpus/test.tsv
```

---

## 📋 Format bàn giao cho TV2

### File `corpus/train.tsv`

```text
# Format: EN TAB VI, mỗi dòng 1 cặp câu
Machine learning is a subset of AI.	Học máy là một tập hợp con của AI.
The model was trained on a large dataset.	Mô hình được huấn luyện trên tập dữ liệu lớn.
```

### Tiêu chuẩn chất lượng

- Encoding: UTF-8, không có BOM
- Số dòng: ≥ 50,000 train, ≥ 5,000 test
- Độ dài câu: `5 ≤ token_count ≤ 100`
- Không có dòng trùng lặp
- Language detection:
  - source = EN
  - target = VI
  - confidence ≥ 0.9

---

## 🧠 Neo4j Knowledge Graph

### Kiểm tra số lượng node

```cypher
MATCH (t:Term)
RETURN count(t) AS total_terms;
```

Yêu cầu:

```text
total_terms >= 500
```

### Kiểm tra số lượng relationship

```cypher
MATCH ()-[r]->()
RETURN count(r) AS total_edges;
```

Yêu cầu:

```text
total_edges >= 1000
```

### Kiểm tra term RAG

```cypher
MATCH (t:Term)
WHERE toLower(replace(t.term, '"', '')) = 'rag'
RETURN t;
```

---

## 🗄️ PostgreSQL Database

Bảng chính:

```text
translation_memory
```

Kiểm tra số dòng:

```sql
SELECT COUNT(*) FROM translation_memory;
```

Xem thử dữ liệu:

```sql
SELECT * FROM translation_memory LIMIT 5;
```

Nếu dùng Docker Compose và Alembic:

```powershell
docker compose exec ai_service alembic current
```

Kết quả mong muốn:

```text
head
```

---

## 🧪 Chạy Tests

### Unit tests

Không cần Docker:

```powershell
pytest tests/test_etl.py tests/test_validators.py -v
```

### Integration tests

Cần PostgreSQL và Neo4j đang chạy:

```powershell
pytest tests/test_db.py tests/test_kg.py -v
```

### Chạy toàn bộ test

```powershell
pytest tests/ -v
```

---

## ✅ Tự kiểm tra checklist bàn giao

```powershell
python scripts\check_handoff.py
```

Output mong muốn:

```text
[PASS] corpus/train.tsv: 52,341 dòng
[PASS] corpus/test.tsv:  5,234 dòng
[PASS] PostgreSQL: kết nối OK, bảng translation_memory: 52,341 rows
[PASS] Neo4j: 523 nodes, 1,247 edges
[PASS] Language detection accuracy: 98.3%
✅ Sẵn sàng bàn giao cho TV2!
```

---

## 📋 Checklist bàn giao Tuần 6

```text
[ ] python scripts/check_handoff.py → tất cả PASS
[ ] pytest tests/ -v → tất cả PASS
[ ] corpus/train.tsv: >= 50,000 dòng
[ ] corpus/test.tsv:  >= 5,000 dòng
[ ] Neo4j: >= 500 nodes, >= 1000 edges
[ ] PostgreSQL: bảng translation_memory có dữ liệu
[ ] DB migration: alembic current → head
[ ] docs/CONTRACT_DATA_TO_AI.md đã viết
[ ] Tạo issue "Handoff TV4→TV2 complete" và tag TV2
[ ] PR "feat: complete data pipeline" → TV1 approve → merge vào main
```

---

## 🧪 Vai trò QA/QC Tuần 10–11

Sau khi hệ thống AI chạy, TV4 thực hiện QA review.

Tải 50 bản dịch từ hệ thống để review:

```powershell
curl http://localhost:8000/translate/batch-sample?n=50 > qa_samples.json
```

Mở file review:

```text
qa_review_log.xlsx
```

Tiêu chí review mỗi bản dịch, thang điểm 1–5:

- Độ chính xác ngữ nghĩa: 40%
- Chuẩn xác thuật ngữ: 30%
- Ngữ pháp tiếng Việt: 15%
- Tính tự nhiên / fluency: 15%

Mục tiêu:

```text
Human score trung bình >= 3.5/5 trên 50 bản dịch
```

---

## ⚠️ Lưu ý

- Không commit thư mục `raw/` nếu dữ liệu lớn.
- Không commit mật khẩu thật trong môi trường production.
- Các giá trị env trong README chỉ dùng cho local/dev.
- Khi chạy script Python ngoài Docker:
  - PostgreSQL dùng `127.0.0.1:5432`
  - Neo4j dùng `localhost:7687`
- Khi chạy trong Docker Compose:
  - PostgreSQL dùng hostname `postgres:5432`
  - Neo4j dùng hostname `neo4j:7687`
- Nếu collector không tải được dữ liệu, kiểm tra quyền chia sẻ Google Drive:
  - phải để `Anyone with the link`
- Nếu thay đổi schema DB, cần tạo migration mới bằng Alembic.
- Nếu thêm thuật ngữ mới vào KG sau Tuần 6, thông báo TV2 để re-index vector database.