# Test Strategy & Tài liệu — TV1 (Leader / BA Lead)

> **Người phụ trách:** TV1  
> **Trách nhiệm:** Quản lý tiến độ · Viết tài liệu · Test Cases · Integration E2E · Demo

---

## 📁 Cấu trúc thư mục TV1 sở hữu

```
tests/
├── e2e/
│   ├── test_full_flow.py        ← Luồng dịch đầu cuối (Upload → Kết quả)
│   ├── test_qa_flow.py          ← Luồng QA review
│   ├── test_auth_flow.py        ← Đăng nhập, phân quyền
│   └── conftest.py              ← Browser driver, base URL
│
├── integration/
│   ├── test_data_to_ai.py       ← TV4 corpus → TV2 AI có đọc được không?
│   ├── test_ai_to_web.py        ← TV2 API → TV3 frontend parse đúng không?
│   └── test_docker_compose.py   ← Tất cả services healthy sau docker compose up?
│
docs/
├── PTTK_DataMining.tex          ← Tài liệu PTTK chính (LaTeX)
├── PTTK_DataMining.pdf          ← PDF xuất từ LaTeX
├── TEST_STRATEGY.md             ← File này
├── CONTRACT_DATA_TO_AI.md       ← Interface contract TV4→TV2
├── CONTRACT_AI_TO_WEB.md        ← Interface contract TV2→TV3
├── MEETING_NOTES/               ← Ghi chú họp nhóm hàng tuần
│   ├── week01.md
│   ├── week02.md
│   └── ...
└── DEMO_SCRIPT.md               ← Kịch bản demo cho giảng viên
```

---

## 📅 Lịch Trình TV1 theo tuần

| Tuần | Công việc chính | Deliverable |
|---|---|---|
| 1–2 | Thu thập YC, phỏng vấn nhóm, vẽ Use Case | Tài liệu SRS, 15+ bảng Use Case |
| 3–4 | Viết PTTK (chương 1–3), vẽ UML diagrams | PTTK draft v1 |
| 4 | Mockup UI/UX trên Figma | 6 màn hình mockup |
| 6 | **Test Gate 1**: Kiểm tra bàn giao TV4→TV2 | Gate 1 report |
| 7 | Theo dõi AI pipeline (TV2), hỗ trợ debug | Meeting notes |
| 8 | **Test Gate 2**: Kiểm tra bàn giao TV2→TV3 | Gate 2 report |
| 9 | Theo dõi integration Docker Compose | - |
| 10 | **Integration Test E2E** (toàn hệ thống) | Test report |
| 10 | Viết Test Cases chi tiết | test_cases.xlsx |
| 11 | QA/QC bổ sung, fix bug cùng nhóm | Bug log |
| 11–12 | Hoàn thiện PTTK (chương 4–6) | PTTK final PDF |
| 12 | Chuẩn bị demo, slide thuyết trình | slide.pptx, demo video |

---

## 🚪 Test Gate Protocol

### Test Gate 1 — Tuần 6: TV4 → TV2

TV1 verify bàn giao bằng cách chạy:

```bash
cd tests/integration
pytest test_data_to_ai.py -v
```

**Kiểm tra:**
```python
# test_data_to_ai.py
def test_corpus_format():
    """TV4 phải cung cấp file đúng format"""
    df = pd.read_csv("data_pipeline/corpus/train.tsv", sep="\t", header=None)
    assert len(df) >= 50000, f"Corpus chỉ có {len(df)} dòng, cần >= 50000"
    assert df.shape[1] == 2, "Phải có đúng 2 cột: EN và VI"

def test_db_migration():
    """Schema PostgreSQL phải đã được migrate"""
    engine = create_engine(os.getenv("DATABASE_URL"))
    inspector = inspect(engine)
    assert "translations" in inspector.get_table_names()
    assert "translation_memory" in inspector.get_table_names()

def test_neo4j_seed():
    """KG phải có đủ thuật ngữ"""
    driver = GraphDatabase.driver(NEO4J_URI)
    with driver.session() as s:
        count = s.run("MATCH (t:Term) RETURN count(t) AS n").single()["n"]
    assert count >= 500, f"KG chỉ có {count} terms, cần >= 500"
```

**Kết quả:** Tạo file `docs/GATE1_REPORT.md` ghi lại kết quả.

---

### Test Gate 2 — Tuần 8: TV2 → TV3

```bash
pytest tests/integration/test_ai_to_web.py -v
```

```python
# test_ai_to_web.py
def test_translate_endpoint():
    """AI Service phải chạy và trả đúng format"""
    r = requests.post("http://localhost:8000/translate", json={
        "file_b64": encode_file("tests/fixtures/sample_en.txt"),
        "file_type": "txt",
        "domain": "computer_science"
    })
    assert r.status_code == 202
    data = r.json()
    assert "job_id" in data
    assert "status" in data

def test_get_translation_result():
    """Polling kết quả phải trả đúng structure"""
    # Giả sử job đã xong
    r = requests.get("http://localhost:8000/translate/test-job-id")
    data = r.json()
    assert "result" in data
    assert "segments" in data["result"]
    segment = data["result"]["segments"][0]
    assert "source" in segment
    assert "target" in segment
    assert "confidence" in segment
    assert "terms_normalized" in segment

def test_bleu_score():
    """BLEU score phải đạt ngưỡng"""
    result = run_bleu_evaluation("data_pipeline/corpus/test.tsv")
    assert result["bleu"] >= 30, f"BLEU = {result['bleu']}, cần >= 30"
```

---

## 🔗 Integration Test E2E — Tuần 10

Chạy sau khi toàn hệ thống lên (docker compose up):

```bash
pytest tests/e2e/ -v --html=docs/e2e_report.html
```

```python
# test_full_flow.py — Luồng dịch đầu cuối

def test_login():
    """Đăng nhập thành công"""
    r = requests.post("http://localhost:80/user/login", json={
        "name": "testuser", "pass": "testpass123"
    })
    assert r.status_code == 200
    assert "access_token" in r.json()

def test_upload_and_translate():
    """Upload PDF → nhận bản dịch song ngữ"""
    token = get_auth_token()
    # 1. Upload
    r = requests.post("http://localhost:8000/translate", 
        headers={"Authorization": f"Bearer {token}"},
        json={"file_b64": SAMPLE_PDF_B64, "file_type": "pdf", "domain": "computer_science"})
    job_id = r.json()["job_id"]
    
    # 2. Poll đến khi xong (tối đa 120s)
    result = poll_until_done(job_id, timeout=120)
    
    # 3. Kiểm tra kết quả
    assert result["status"] == "completed"
    assert len(result["result"]["segments"]) > 0
    assert result["result"]["bleu_score"] > 0

def test_term_highlight():
    """Thuật ngữ phải được normalize trong bản dịch"""
    result = translate_text("RAG is a technique that combines retrieval with generation.")
    segment = result["segments"][0]
    assert "RAG" in segment["terms_normalized"]
    # "RAG" → "Tạo sinh tăng cường" (lấy từ KG)

def test_qa_review_flow():
    """QA Reviewer có thể sửa và phê duyệt bản dịch"""
    reviewer_token = get_auth_token("reviewer_user")
    r = requests.post(f"http://localhost:8000/reviews/{SAMPLE_JOB_ID}/submit",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"corrected_text": "Học máy...", "score": 4, "comment": "Tốt"})
    assert r.status_code == 200
    assert r.json()["status"] == "approved"
```

---

## 📝 Cách tạo & merge PR đúng quy trình

TV1 là người review và merge PR từ các thành viên khác.

**Checklist review PR:**
```
[ ] Code chạy được: docker compose up không lỗi
[ ] Tests PASS: pytest <module>/tests/ -v
[ ] Không hardcode URL, credentials
[ ] Commit message đúng format: [TVx] type: mô tả
[ ] Không commit file lớn (model weights, raw data)
[ ] Không commit .env file
[ ] PR description đầy đủ: What / Why / How to test
```

---

## 🎯 Chuẩn bị Demo (Tuần 12)

**Kịch bản demo 10 phút:**

1. **(1 phút)** Giới thiệu hệ thống, kiến trúc 4 phân hệ
2. **(3 phút)** Demo dịch tài liệu:
   - Upload PDF abstract từ arXiv (tiếng Anh)
   - Xem tiến trình dịch real-time
   - Xem bản dịch song ngữ, highlight thuật ngữ
   - Download file kết quả
3. **(2 phút)** Demo QA Review:
   - Đăng nhập với tài khoản Reviewer
   - Xem bản dịch cần review, chỉnh sửa, phê duyệt
4. **(2 phút)** Demo Dashboard Superset BI:
   - Xem 4 charts: lượt dịch, BLEU trend, top thuật ngữ
5. **(1 phút)** Demo Mobile App:
   - Dịch đoạn văn ngắn trên điện thoại
6. **(1 phút)** Kết luận, hướng phát triển

**File cần chuẩn bị sẵn:**
- `tests/fixtures/arxiv_sample.pdf` — Abstract khoa học tiếng Anh ~500 chữ
- Tài khoản demo: `demo_user` / `Demo@123`, `reviewer` / `Review@123`
- Ghi video backup phòng trường hợp mạng chậm
