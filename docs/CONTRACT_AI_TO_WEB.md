# Contract: TV2 (AI) → TV3 (Web/Mobile)
# Tuần bàn giao: Tuần 8

> Lưu ý stack TV3: client Web/Mobile dùng Flutter/Dart. Contract này chỉ quy định HTTP/JSON API và giữ độc lập với cách triển khai UI.

## Trạng thái bàn giao lại

Sau rà soát ngày 2026-05-10, AI Service hiện mới expose bản demo đồng bộ:

- `POST /translate/` nhận `text`, trả `translated_text`.
- `GET /terms/` trả danh sách term mẫu.
- Chưa có `POST /translate/` nhận file/base64 và trả `job_id`.
- Chưa có `GET /translate/{job_id}` để TV3 poll kết quả.
- Chưa có `GET /terms/lookup`.
- `ai_service/docs/openapi.json`, `ai_service/docs/postman_collection.json`, `ai_service/docs/API_SPEC.md` đang mô tả demo sync, chưa khớp contract bên dưới.

Vì vậy TV2 cần hoàn tất phần "Nhiệm vụ TV2 trước khi bàn giao lại" trước khi TV3 tích hợp API thật. Trong thời gian chờ, TV3 dùng mock client theo contract này.

## TV2 cam kết cung cấp

| Item | Đường dẫn / URL | Mô tả |
|---|---|---|
| API endpoint | `POST localhost:8000/translate` | Nhận file, trả job_id |
| API endpoint | `GET localhost:8000/translate/{id}` | Lấy kết quả |
| API endpoint | `GET localhost:8000/terms/lookup` | Tra thuật ngữ |
| OpenAPI spec | `ai_service/docs/openapi.json` | Tự động từ FastAPI |
| Postman collection | `ai_service/docs/postman_collection.json` | Import test ngay |
| BLEU score | ≥ 30 trên test.tsv | Kết quả eval |

## Nhiệm vụ TV2 trước khi bàn giao lại

1. Chuẩn hóa schema Pydantic cho request/response đúng contract.
2. Implement `POST /translate/` async: nhận `file_b64`, `file_type`, `domain`; trả HTTP `202` với `job_id`, `status`, `estimated_seconds`.
3. Implement job store tối thiểu bằng Redis hoặc in-memory trong dev; trạng thái gồm `pending`, `processing`, `completed`, `failed`.
4. Implement `GET /translate/{job_id}` để trả trạng thái và result theo format đã cam kết.
5. Implement decode/extract nội dung file cho `txt` trước; `pdf` và `docx` phải có lỗi rõ ràng nếu chưa hỗ trợ đầy đủ.
6. Implement `GET /terms/lookup?q=...&domain=...` dùng KG nếu Neo4j sẵn sàng, fallback glossary nếu KG chưa có data.
7. Cập nhật `ai_service/docs/openapi.json`, `ai_service/docs/postman_collection.json`, `ai_service/docs/API_SPEC.md` theo endpoint thật.
8. Bổ sung tests: `test_api.py`, `test_terms.py`, và test contract response shape.
9. Chạy lại BLEU eval và ghi rõ thang điểm: nếu dùng sacreBLEU `0-100`, giá trị phải `>= 30`; nếu log dạng `0.x`, phải quy đổi trước khi báo cáo.
10. Gửi lại bằng issue `[Handoff] TV2→TV3 re-handoff complete` kèm lệnh test và kết quả.

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
