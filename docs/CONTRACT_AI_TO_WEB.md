# Contract: TV2 (AI) → TV3 (Web/Mobile)
# Tuần bàn giao: Tuần 8

## TV2 cam kết cung cấp

| Item | Đường dẫn / URL | Mô tả |
|---|---|---|
| API endpoint | `POST localhost:8000/translate` | Nhận file, trả job_id |
| API endpoint | `GET localhost:8000/translate/{id}` | Lấy kết quả |
| API endpoint | `GET localhost:8000/terms/lookup` | Tra thuật ngữ |
| OpenAPI spec | `ai_service/docs/openapi.json` | Tự động từ FastAPI |
| Postman collection | `ai_service/docs/postman_collection.json` | Import test ngay |
| BLEU score | ≥ 30 trên test.tsv | Kết quả eval |

## Response format cam kết (không thay đổi sau W8)

```json
// GET /translate/{job_id} → completed
{
  "job_id": "string",
  "status": "completed",
  "result": {
    "segments": [
      {
        "source": "string",
        "target": "string", 
        "confidence": 0.0,
        "terms_normalized": {}
      }
    ],
    "bleu_score": 0.0,
    "word_count": 0,
    "processing_time_ms": 0
  }
}
```

## TV3 cam kết kiểm tra

Chạy `pytest ai_service/tests/ -v` → tất cả PASS.  
Upload file PDF thật → nhận kết quả trong < 120s.

## Xác nhận

TV2 tạo issue: `[Handoff] TV2→TV3 complete - Week 8`  
TV3 comment: `✅ Verified - <date>`  
TV1 close issue.

## Quy trình thay đổi API sau W8

Nếu TV2 cần thay đổi response format:
1. Tạo issue `[API Change] /endpoint - mô tả thay đổi`
2. Assign TV3 và TV1
3. Chờ TV3 confirm có thể adapt
4. Thay đổi, update openapi.json, notify TV3
