# Bàn giao lại TV2 -> TV3

Tài liệu này dành cho TV3 tích hợp Web/Mobile với AI Service của TV2.

Stack client của TV3 là Flutter/Dart cho cả Web và Mobile; các ví dụ client trong tài liệu này ưu tiên Dart để có thể dùng chung.

Nguồn đã đối chiếu:

- `ai_service/README.md`
- `ai_service/docs/API_SPEC.md`
- `ai_service/docs/openapi.json`
- `docs/CONTRACT_AI_TO_WEB.md`
- `ai_service/docs/postman_collection.json`

## Checklist trạng thái bàn giao TV2 -> TV3

Ngày rà soát: 2026-05-10. Kết luận: AI Service **chưa đủ điều kiện bàn giao API thật cho TV3** theo contract async/file-based. Hiện trạng tốt nhất là bản demo dịch text đồng bộ; TV3 nên dùng mock client theo contract cho đến khi TV2 đóng các mục "Chưa có" và "Có một phần".

| # | Hạng mục TV2 cần bàn giao | Nội dung TV3 cần nhận | Trạng thái | Bằng chứng / ghi chú |
|---:|---|---|---|---|
| 1 | Runtime AI Service local | Service chạy tại `http://localhost:8000` | Đã có | `docker compose ps` cho thấy `sci_ai_service` healthy; `GET /health/` trả `200`. |
| 2 | Health check | `GET /health/` để TV3 kiểm tra service sống | Đã có | Response live có `status: ok`, `service: SCI Translate AI Service`. |
| 3 | `POST /translate/` demo text | Dịch text ngắn trực tiếp để test nhanh | Đã có - demo | Body `text/source_lang/target_lang` trả `original_text`, `translated_text`, `source_lang`, `target_lang`. Đây không phải contract bàn giao cuối. |
| 4 | `POST /translate/` theo contract | Nhận `file_b64`, `file_type`, `domain`; trả `job_id`, `status`, `estimated_seconds` | Chưa có | Gửi body contract live trả `422` vì thiếu field `text`; route hiện tại chỉ nhận text. |
| 5 | `GET /translate/{job_id}` | TV3 poll trạng thái job: `pending`, `processing`, `completed`, `failed` | Chưa có | Gọi live `GET /translate/test-job-id` trả `404`; không có route trong `api/routes/translate.py`. |
| 6 | Job store / async processing | Lưu job và kết quả bằng Redis hoặc in-memory dev; có worker xử lý nền | Có một phần | Có Redis/RabbitMQ trong compose và file Celery placeholder, nhưng chưa gắn với API; compose chưa có service worker riêng. |
| 7 | Response result song ngữ | `result.segments[]`, `bleu_score`, `word_count`, `processing_time_ms` | Chưa có | Response hiện tại chỉ có một chuỗi `translated_text`, chưa có segment hoặc metadata. |
| 8 | Decode file input | Hỗ trợ tối thiểu `txt`; `pdf/docx` hoặc chạy được hoặc trả lỗi rõ ràng | Chưa có | Không thấy logic decode `file_b64`, extract TXT/PDF/DOCX trong route/schema. |
| 9 | `GET /terms/lookup` | Tra thuật ngữ theo `q` và `domain` | Chưa có | Gọi live `/terms/lookup?q=RAG` trả `404`; `terms.py` chỉ expose `GET /terms/`. |
| 10 | `GET /terms/` demo | Danh sách term mẫu để smoke test | Đã có - demo | Trả 3 term mẫu: machine learning, deep learning, transformer. Không thay thế được `/terms/lookup`. |
| 11 | KG cho thuật ngữ | Dùng Neo4j để lấy thuật ngữ chuyên ngành, có fallback glossary | Có một phần | `KGQueryService` được gọi trong translate flow; chưa có public lookup endpoint và chưa có bằng chứng seed KG đáp ứng term lookup cho TV3. |
| 12 | RAG/vectorstore | Context tương tự từ Chroma/vectorstore khi dịch | Có một phần | Route translate có gọi `build_rag_examples`; repo có vectorstore. TV3 không gọi trực tiếp, nhưng TV2 cần xác nhận index reproducible. |
| 13 | OpenAPI machine-readable | `ai_service/docs/openapi.json` và `/openapi.json` mô tả đúng contract | Có một phần | File tồn tại và live endpoint trả được, nhưng chỉ có `/health/`, `/translate/` text sync, `/terms/`; thiếu `/translate/{job_id}` và `/terms/lookup`. |
| 14 | Postman collection | Collection test đủ 3 endpoint contract | Có một phần | File tồn tại nhưng chỉ có Health Check, Translate Text, Terms demo. |
| 15 | API spec cho TV3 | `API_SPEC.md` mô tả đúng request/response cuối | Có một phần | Spec hiện tại mô tả demo sync text và `GET /terms/`, chưa mô tả async job thật. |
| 16 | Schema Pydantic dùng chung | Request/response model khớp contract và được route import dùng | Có một phần | `schemas/translate.py` và `schemas/term.py` vẫn là placeholder; route đang định nghĩa model riêng trong file. |
| 17 | Auth/JWT contract | TV3 gửi `Authorization: Bearer <token>` và API xử lý/validate nhất quán | Chưa có | `api/deps.py` là placeholder; route hiện tại không enforce auth. |
| 18 | CORS cho Flutter Web | Cho phép Flutter web gọi API trong dev | Đã có | `main.py` cấu hình `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]`. |
| 19 | Test bàn giao API | `test_api.py`, `test_terms.py`, contract response shape test | Chưa có | Trong `ai_service/tests` hiện chỉ thấy `test_ollama.py` và `conftest.py`. |
| 20 | Test engine hiện có | Unit test engine không cần Ollama thật | Đã có | Chạy từ `ai_service`: `py -m pytest tests -v` -> `15 passed`. Chạy từ root lỗi import `models`, nên lệnh bàn giao cần ghi rõ cwd hoặc sửa package path. |
| 21 | BLEU report | Kết quả BLEU trên test set, ghi rõ thang điểm | Có một phần | Có `ai_service/models/BLEU_Ver1`, ghi Corpus BLEU `0.3971`; contract cũ yêu cầu `>= 30`, cần chốt quy đổi `39.71` hoặc chạy lại sacreBLEU chuẩn. |
| 22 | Model/Ollama setup | Model chính thức, lệnh pull, base URL, timeout | Có một phần | Tài liệu/env chưa nhất quán: có nơi dùng `qwen2.5:3b`, có nơi `qwen2.5:7b`, `ai_service/.env.example` còn để `gemma2`. |
| 23 | Docker Compose dependencies | TV3 chạy được stack phụ thuộc AI: Redis, RabbitMQ, Neo4j, ChromaDB | Đã có | Stack live có đủ 8 service: postgres, neo4j, chromadb, redis, rabbitmq, ai_service, drupal, superset. |
| 24 | Handoff evidence | Issue/PR bàn giao kèm commit, lệnh test, kết quả test, link Swagger/Postman | Chưa có | Chưa thấy bằng chứng handoff hoàn tất trong repo; cần tạo issue `[Handoff] TV2→TV3 re-handoff complete`. |

### Các mục chặn bàn giao thật cho TV3

- `POST /translate/` file/base64 async chưa có.
- `GET /translate/{job_id}` chưa có.
- `GET /terms/lookup` chưa có.
- OpenAPI/Postman/API spec chưa khớp contract.
- Test API contract chưa có.
- BLEU cần chạy lại hoặc chuẩn hóa thang điểm trước khi báo cáo đạt `>= 30`.
- Model/Ollama config cần chốt một giá trị chính thức để TV3 setup giống TV2.

> Lưu ý trạng thái hiện tại: contract trong `docs/CONTRACT_AI_TO_WEB.md` mô tả API bất đồng bộ `POST /translate/` -> `job_id`, `GET /translate/{job_id}`, `GET /terms/lookup`. OpenAPI/Postman hiện tại đang expose bản demo đồng bộ gồm `GET /health/`, `POST /translate/` theo text và `GET /terms/`. TV3 nên code Flutter client theo contract bên dưới, đồng thời dùng mock client cho các endpoint async cho đến khi OpenAPI/Postman được TV2 cập nhật đủ.

---

## 0. Phạm vi TV2 cần bàn giao lại

### Kết luận rà soát

AI Service hiện chạy được demo dịch text đồng bộ, nhưng chưa đủ để TV3 tích hợp flow Flutter theo contract chính thức. TV2 cần bổ sung các endpoint async/file-based và tài liệu test trước khi bàn giao lại.

### Thứ tự thực hiện cho TV2

1. Chốt contract với TV3: giữ nguyên `POST /translate/`, `GET /translate/{job_id}`, `GET /terms/lookup`; không đổi field nếu chưa có issue `[API Change]`.
2. Sửa schema trong `ai_service/schemas/translate.py` và route `ai_service/api/routes/translate.py`.
3. Implement `POST /translate/` nhận `file_b64`, `file_type`, `domain`; trả `202 Accepted` với `job_id`.
4. Implement job store và `GET /translate/{job_id}` để TV3 poll `pending -> processing -> completed/failed`.
5. Implement extract file tối thiểu:
   - `txt`: bắt buộc chạy được.
   - `pdf`, `docx`: chạy được nếu kịp; nếu chưa, trả lỗi rõ ràng `400/422` với message cụ thể.
6. Implement `GET /terms/lookup?q=...&domain=...`; ưu tiên KG/Neo4j, có fallback glossary tĩnh để demo không bị 404.
7. Cập nhật tài liệu máy đọc:
   - `ai_service/docs/openapi.json`
   - `ai_service/docs/postman_collection.json`
   - `ai_service/docs/API_SPEC.md`
8. Bổ sung tests tối thiểu:
   - `ai_service/tests/test_api.py`: test `POST /translate/`, `GET /translate/{job_id}`.
   - `ai_service/tests/test_terms.py`: test `/terms/lookup`.
   - Test response shape có đủ `segments`, `bleu_score`, `word_count`, `processing_time_ms`.
9. Chạy lại BLEU eval, ghi rõ thang điểm. Nếu output script là `0.3971`, báo cáo theo thang `0-1`; nếu contract yêu cầu `>= 30`, cần quy đổi hoặc dùng corpus BLEU `39.71`.
10. Gửi issue `[Handoff] TV2→TV3 re-handoff complete` kèm:
    - Commit/PR link.
    - Lệnh đã chạy.
    - Kết quả test.
    - Link Swagger/OpenAPI/Postman đã cập nhật.

### Definition of Done

TV2 chỉ được coi là bàn giao lại xong khi các lệnh sau đạt kết quả đúng:

```powershell
curl http://localhost:8000/health/
curl -X POST http://localhost:8000/translate/ `
  -H "Content-Type: application/json" `
  -d "{\"file_b64\":\"SGVsbG8=\",\"file_type\":\"txt\",\"domain\":\"general\"}"
curl http://localhost:8000/translate/<job_id>
curl "http://localhost:8000/terms/lookup?q=RAG&domain=computer_science"
pytest ai_service/tests/ -v
```

Kết quả bắt buộc:

- `POST /translate/` trả `202` hoặc `200` có `job_id`.
- `GET /translate/{job_id}` trả `completed` có `result.segments`.
- `GET /terms/lookup` không trả `404`.
- OpenAPI/Postman mô tả đúng 3 endpoint contract, không chỉ demo sync.

---

## 1. Tổng quan TV2 đã bàn giao

### Stack công nghệ

- Backend: Python 3.11, FastAPI, Uvicorn.
- Translation engine: Ollama local.
- Model hiện dùng: `qwen2.5:3b`.
- RAG: LangChain + ChromaDB/vectorstore từ corpus song ngữ.
- KG: Neo4j Knowledge Graph để tra thuật ngữ chuyên ngành.
- Cache/queue: Redis, RabbitMQ/Celery theo thiết kế async.
- Container: Docker Compose.

### Model và phần cứng

- Cần cài Ollama trên máy host, không chạy trong container.
- Cần pull model:

```powershell
ollama pull qwen2.5:3b
ollama list
```

- RAM tối thiểu nên có: 8 GB.
- RAM khuyến nghị: 16 GB.
- GPU không bắt buộc; nếu có NVIDIA GPU thì Ollama tự tận dụng và dịch nhanh hơn.

### BLEU score

Kết quả lưu trong `ai_service/models/BLEU_Ver1`:

- Evaluated: `1000` samples
- Skipped: `31` samples
- Sentence BLEU: `0.3728`
- Corpus BLEU: `0.3971`
- Quality: `ACCEPTABLE`

Contract cũ ghi mục tiêu `BLEU >= 30`; nếu cần báo cáo theo thang 0-100, TV2 cần chạy lại eval và chuẩn hóa số liệu trước demo chính thức.

### File/thư mục TV3 cần biết

| Path | Ý nghĩa |
|---|---|
| `ai_service/README.md` | Mô tả stack, cách chạy service |
| `ai_service/docs/API_SPEC.md` | API spec demo hiện tại |
| `ai_service/docs/openapi.json` | OpenAPI schema export từ FastAPI |
| `ai_service/docs/postman_collection.json` | Collection Postman để test nhanh |
| `docs/CONTRACT_AI_TO_WEB.md` | Contract TV2 -> TV3 đã cam kết |
| `ai_service/main.py` | FastAPI app, include routers |
| `ai_service/api/routes/translate.py` | Endpoint translate hiện tại |
| `ai_service/api/routes/terms.py` | Endpoint terms hiện tại |
| `ai_service/models/ollama_config.py` | Cấu hình Ollama/model |
| `ai_service/rag/` | RAG pipeline, TV3 không cần sửa |
| `ai_service/kg/` | Neo4j/KG, TV3 không cần sửa |
| `docker-compose.yml` | Chạy toàn bộ stack local |
| `.env.example` | Biến môi trường mẫu |

---

## 2. Môi trường TV3 cần chuẩn bị

### Bắt buộc

- Docker Desktop đang chạy.
- Ollama đã cài và đang chạy trên host.
- Model `qwen2.5:3b` đã pull.
- File `.env` đã tạo từ `.env.example`.

```powershell
copy .env.example .env
ollama pull qwen2.5:3b
docker compose up -d
```

### Services cần chạy

TV3 tối thiểu cần các service sau:

- `postgres`
- `neo4j`
- `redis`
- `ai_service`

Các service phụ có thể chạy cùng stack:

- `chromadb`
- `rabbitmq`
- `drupal`
- `superset`

### Kiểm tra môi trường sẵn sàng

```powershell
docker compose ps
curl http://localhost:8000/health/
curl http://localhost:8000/openapi.json
ollama list
```

Kết quả mong đợi:

- `sci_postgres`: healthy
- `sci_neo4j`: healthy
- `sci_redis`: healthy
- `sci_ai_service`: healthy/running
- `/health/`: HTTP `200`
- `ollama list`: có `qwen2.5:3b`

---

## 3. API Contract TV3 sẽ gọi

Base URL local:

```text
http://localhost:8000
```

Với Android emulator:

```text
http://10.0.2.2:8000
```

Header auth theo contract:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

> Demo local hiện tại chưa enforce Bearer token trong OpenAPI, nhưng TV3 vẫn nên implement header này để khớp contract khi auth được bật.

### 3.1. POST `/translate/`

Tạo job dịch tài liệu.

#### Request

```json
{
  "file_b64": "<base64 encoded PDF/DOCX/TXT>",
  "file_type": "pdf",
  "domain": "computer_science"
}
```

| Field | Type | Required | Ghi chú |
|---|---|---:|---|
| `file_b64` | string | Yes | Nội dung file đã base64 |
| `file_type` | string | Yes | `pdf`, `docx`, `txt` |
| `domain` | string | No | `computer_science`, `biology`, `physics`, `chemistry`, `general` |

#### Response `202 Accepted`

```json
{
  "job_id": "uuid-xxxx",
  "status": "pending",
  "estimated_seconds": 30
}
```

#### Curl

```bash
curl -X POST "http://localhost:8000/translate/" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "file_b64": "<base64>",
    "file_type": "pdf",
    "domain": "computer_science"
  }'
```

#### Flutter/Dart

```dart
import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;

Future<String> createTranslateJob({
  required String baseUrl,
  required String token,
  required Uint8List fileBytes,
  required String fileType,
  String domain = 'computer_science',
}) async {
  final body = {
    'file_b64': base64Encode(fileBytes),
    'file_type': fileType,
    'domain': domain,
  };

  final res = await http.post(
    Uri.parse('$baseUrl/translate/'),
    headers: {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    },
    body: jsonEncode(body),
  );

  if (res.statusCode != 202 && res.statusCode != 200) {
    throw Exception('Create translate job failed: ${res.statusCode} ${res.body}');
  }

  final json = jsonDecode(res.body) as Map<String, dynamic>;
  return json['job_id'] as String;
}
```

> Demo sync hiện tại trong OpenAPI dùng body `{"text":"...","source_lang":"en","target_lang":"vi"}` và trả trực tiếp `translated_text`. TV3 chỉ dùng format demo này để test local nếu endpoint async chưa sẵn sàng.

---

### 3.2. GET `/translate/{job_id}`

Lấy trạng thái/kết quả job dịch.

#### Request

```http
GET /translate/{job_id}
Authorization: Bearer <access_token>
```

#### Response khi `pending`

```json
{
  "job_id": "uuid-xxxx",
  "status": "pending"
}
```

#### Response khi `processing`

```json
{
  "job_id": "uuid-xxxx",
  "status": "processing",
  "progress": 45
}
```

#### Response khi `completed`

```json
{
  "job_id": "uuid-xxxx",
  "status": "completed",
  "result": {
    "segments": [
      {
        "source": "Machine learning is a subset of AI.",
        "target": "Học máy là một tập con của AI.",
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

#### Response khi `failed`

```json
{
  "job_id": "uuid-xxxx",
  "status": "failed",
  "error": "Ollama service unavailable"
}
```

#### Curl

```bash
curl "http://localhost:8000/translate/<job_id>" \
  -H "Authorization: Bearer <access_token>"
```

#### Flutter/Dart: get status

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

Future<Map<String, dynamic>> getTranslateJob({
  required String baseUrl,
  required String token,
  required String jobId,
}) async {
  final res = await http.get(
    Uri.parse('$baseUrl/translate/$jobId'),
    headers: {'Authorization': 'Bearer $token'},
  );

  if (res.statusCode != 200) {
    throw Exception('Get translate job failed: ${res.statusCode} ${res.body}');
  }

  return jsonDecode(res.body) as Map<String, dynamic>;
}
```

#### Flutter/Dart: poll đến khi completed

```dart
Future<Map<String, dynamic>> waitForTranslateResult({
  required String baseUrl,
  required String token,
  required String jobId,
  Duration interval = const Duration(seconds: 2),
  Duration timeout = const Duration(seconds: 120),
}) async {
  final startedAt = DateTime.now();

  while (DateTime.now().difference(startedAt) < timeout) {
    final job = await getTranslateJob(
      baseUrl: baseUrl,
      token: token,
      jobId: jobId,
    );

    final status = job['status'] as String?;
    if (status == 'completed') return job;
    if (status == 'failed') {
      throw Exception('Translate job failed: ${job['error']}');
    }

    await Future.delayed(interval);
  }

  throw TimeoutException('Translate job timeout');
}
```

Nếu dùng snippet trên, thêm import:

```dart
import 'dart:async';
```

---

### 3.3. GET `/terms/lookup`

Tra thuật ngữ chuyên ngành.

#### Request query params

```http
GET /terms/lookup?q=RAG&domain=computer_science
Authorization: Bearer <access_token>
```

| Query param | Type | Required | Ghi chú |
|---|---|---:|---|
| `q` | string | Yes | Thuật ngữ cần tra |
| `domain` | string | No | Domain chuyên ngành |

#### Response `200 OK`

```json
{
  "term_en": "RAG",
  "term_vi": "Tạo sinh tăng cường truy xuất",
  "definition_vi": "Kỹ thuật kết hợp truy xuất thông tin với mô hình ngôn ngữ.",
  "domain": "computer_science",
  "related_terms": ["LLM", "Embedding", "Vector Database"]
}
```

#### Curl

```bash
curl "http://localhost:8000/terms/lookup?q=RAG&domain=computer_science" \
  -H "Authorization: Bearer <access_token>"
```

#### Flutter/Dart

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

Future<Map<String, dynamic>> lookupTerm({
  required String baseUrl,
  required String token,
  required String query,
  String domain = 'computer_science',
}) async {
  final uri = Uri.parse('$baseUrl/terms/lookup').replace(
    queryParameters: {
      'q': query,
      'domain': domain,
    },
  );

  final res = await http.get(
    uri,
    headers: {'Authorization': 'Bearer $token'},
  );

  if (res.statusCode != 200) {
    throw Exception('Lookup term failed: ${res.statusCode} ${res.body}');
  }

  return jsonDecode(res.body) as Map<String, dynamic>;
}
```

> Demo OpenAPI hiện tại chỉ có `GET /terms/`, trả danh sách term mẫu. `GET /terms/lookup` là contract TV3 cần code theo.

---

## 4. Test API trước khi code

### Swagger UI

Mở:

```text
http://localhost:8000/docs
```

Kiểm tra nhanh:

- `GET /health/`
- `POST /translate/`
- `GET /terms/`

### Import Postman collection

1. Mở Postman.
2. Import file `ai_service/docs/postman_collection.json`.
3. Tạo environment variable:

```text
baseUrl=http://localhost:8000
token=<access_token>
```

4. Với request cần auth, thêm header:

```text
Authorization: Bearer {{token}}
```

### Lấy Bearer token để test

- Local demo hiện tại: API chưa enforce token, có thể test Swagger/Postman không token.
- Khi tích hợp với auth thật: lấy access token từ TV1/auth service hoặc từ flow login của Web/Mobile.
- TV3 vẫn nên viết API client luôn truyền `Authorization: Bearer <token>`.

### Checklist test

| Test | Expected | Pass/Fail |
|---|---|---|
| Docker Desktop running | Docker command chạy được | `[ ]` |
| `ollama list` | Có `qwen2.5:3b` | `[ ]` |
| `docker compose ps` | `postgres`, `neo4j`, `redis`, `ai_service` running/healthy | `[ ]` |
| `GET /health/` | HTTP `200` | `[ ]` |
| `POST /translate/` demo text | Trả `translated_text` | `[ ]` |
| `POST /translate/` contract | Trả `job_id` khi endpoint async sẵn sàng | `[ ]` |
| `GET /translate/{job_id}` | Poll được `completed` khi endpoint async sẵn sàng | `[ ]` |
| `GET /terms/lookup` | Trả term detail khi endpoint lookup sẵn sàng | `[ ]` |

---

## 5. Thứ tự TV3 cần làm

### Bước 1: Setup môi trường

```powershell
copy .env.example .env
ollama pull qwen2.5:3b
docker compose up -d
docker compose ps
```

### Bước 2: Verify API hoạt động

```powershell
curl http://localhost:8000/health/
curl http://localhost:8000/openapi.json
```

Vào Swagger:

```text
http://localhost:8000/docs
```

### Bước 3: Làm mock API client trước

Mock đúng 3 method:

- `createTranslateJob(...)`
- `getTranslateJob(jobId)`
- `lookupTerm(q, domain)`

Mock status job theo thứ tự:

```text
pending -> processing -> completed
```

### Bước 4: Tích hợp API thật

- Đổi `baseUrl` sang `http://localhost:8000` hoặc URL môi trường dev.
- Gắn Bearer token vào header.
- Bắt lỗi HTTP theo bảng ở phần 7.
- Với Android emulator dùng `http://10.0.2.2:8000`.

### Bước 5: Test end-to-end

- Upload file thật.
- Nhận `job_id`.
- Poll đến `completed`.
- Render danh sách `segments`.
- Gọi `/terms/lookup` khi user bấm vào thuật ngữ.
- Test case lỗi: thiếu token, sai endpoint, Ollama tắt, job failed.

---

## 6. TV3 không cần quan tâm

TV3 chỉ gọi API, không cần đọc/sửa các phần này:

- Ollama internals.
- Prompt/system prompt.
- RAG pipeline.
- Vectorstore/ChromaDB.
- Neo4j Knowledge Graph.
- Celery workers/RabbitMQ.
- BLEU evaluation script.
- Corpus/indexer.

Nếu các phần trên lỗi, báo đúng team theo phần 8.

---

## 7. Lỗi thường gặp

| Lỗi | Nguyên nhân | Fix |
|---|---|---|
| `401 Unauthorized` | Thiếu hoặc sai Bearer token | Login lại/lấy token mới, thêm `Authorization: Bearer <token>` |
| `404 Not Found` | Sai endpoint URL hoặc endpoint async chưa được bật | Kiểm tra `/docs`, dùng đúng `/translate/`, `/translate/{job_id}`, `/terms/lookup` |
| `422 Unprocessable Entity` | Body sai format hoặc thiếu field required | So lại request JSON với contract |
| `503 Service Unavailable` | Ollama chưa chạy hoặc không reachable | Mở Ollama, chạy `ollama list`, kiểm tra `OLLAMA_BASE_URL` |
| `model not found` | Chưa pull `qwen2.5:3b` hoặc `.env` sai model | `ollama pull qwen2.5:3b`, kiểm tra `OLLAMA_MODEL=qwen2.5:3b` |
| `job` mãi `pending` | Celery worker/RabbitMQ chưa chạy hoặc worker lỗi | `docker compose ps`, xem logs `ai_service`, `rabbitmq`, worker |
| `neo4j unhealthy` | Sai password Neo4j so với volume cũ | Dùng password cũ hoặc nhờ TV2/TV1 reset auth không xóa graph data |
| `connection refused 11434` | Container không gọi được Ollama host | Đảm bảo Ollama chạy, dùng `http://host.docker.internal:11434` trong Docker |
| Timeout khi dịch | Đoạn dài/model chậm | Hiển thị loading, tăng timeout client, poll theo job async |

---

## 8. Liên hệ khi có vấn đề

| Vấn đề | Liên hệ |
|---|---|
| Lỗi API, response format, model, dịch sai | TV2 |
| Lỗi Docker Compose, port, container, network | TV1 |
| Lỗi corpus, thuật ngữ, data, KG seed data | TV4 |
| Lỗi UI/Web/Mobile integration | TV3 |

Khi báo lỗi, gửi kèm:

- Endpoint đã gọi.
- Request body/query params.
- HTTP status code.
- Response body.
- Log liên quan:

```powershell
docker logs sci_ai_service --tail 100
docker compose ps
```
