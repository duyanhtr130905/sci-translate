# Frontend & CMS & BI — TV3 (Flutter Web & Mobile Developer)

> **Người phụ trách:** TV3  
> **Stack:** Flutter 3.x · Dart · Drupal 10 · Apache Superset · Docker  
> **Phụ thuộc:** AI Service của TV2 (Tuần 8 mới có API)

> Quy ước hiện tại: `frontend/web` là Flutter project dùng chung cho Web và Mobile. Nếu TV3 tách thêm `frontend/mobile`, project đó vẫn dùng Flutter/Dart và tái sử dụng cùng API contract.

---

## 📁 Cấu trúc thư mục

```
frontend/
└── web/                         ← Flutter app: Web + Android/iOS
    ├── lib/
    │   ├── main.dart
    │   ├── app.dart
    │   ├── core/
    │   │   ├── config/
    │   │   │   └── app_config.dart        ← Đọc --dart-define / .env
    │   │   └── auth/
    │   │       └── token_store.dart       ← JWT token management
    │   ├── features/
    │   │   ├── translate/
    │   │   │   ├── translate_page.dart    ← Trang dịch chính
    │   │   │   └── widgets/
    │   │   │       ├── translate_form.dart
    │   │   │       └── bilingual_view.dart
    │   │   ├── history/
    │   │   │   └── history_page.dart
    │   │   ├── terms/
    │   │   │   ├── terms_page.dart
    │   │   │   └── term_tooltip.dart
    │   │   ├── review/
    │   │   │   └── review_page.dart       ← QA review (chỉ Reviewer)
    │   │   └── dashboard/
    │   │       └── dashboard_link.dart    ← Link đến Superset
    │   └── services/
    │       ├── ai_client.dart             ← Gọi AI Service (localhost:8000)
    │       ├── drupal_client.dart         ← Gọi Drupal REST API (localhost:80)
    │       └── mocks/
    │           └── mock_ai_client.dart
    ├── test/
    ├── integration_test/
    ├── web/
    ├── android/
    ├── ios/
    ├── pubspec.yaml
    └── README.md

cms/                             ← Drupal 10
├── modules/custom/
│   └── sci_translate_api/      ← Custom module: proxy AI calls, lưu lịch sử
│       ├── sci_translate_api.info.yml
│       ├── sci_translate_api.routing.yml
│       └── src/Controller/
│           └── TranslateController.php
├── themes/custom/
│   └── sci_translate_theme/
├── config/                      ← Drupal config export (commit lên git)
└── README.md

analytics/
└── superset/
    ├── dashboards/
    │   └── sci_translate_dashboard.json   ← Export từ Superset, commit lên git
    ├── datasets/                          ← SQL queries cho từng chart
    │   ├── daily_translations.sql
    │   ├── bleu_score_trend.sql
    │   ├── top_terms.sql
    │   └── domain_distribution.sql
    └── README.md
```

---

## 🚀 Chạy Flutter Web (Development)

```bash
cd frontend/web
flutter pub get
flutter run -d chrome --web-port=3000 \
  --dart-define=AI_SERVICE_URL=http://localhost:8000 \
  --dart-define=DRUPAL_URL=http://localhost:80 \
  --dart-define=SUPERSET_URL=http://localhost:8088
# → http://localhost:3000
```

**Cấu hình API endpoints:**

TV3 có thể dùng `--dart-define` như trên, hoặc dùng `.env` nếu app đã tích hợp `flutter_dotenv`.

```env
AI_SERVICE_URL=http://localhost:8000
DRUPAL_URL=http://localhost:80
SUPERSET_URL=http://localhost:8088
USE_MOCK=false
```

**⚠️ Trước Tuần 8 (chưa có AI Service):** dùng mock client:

```bash
flutter run -d chrome --web-port=3000 --dart-define=USE_MOCK=true
# Mock data nằm ở: lib/services/mocks/
```

## 📱 Chạy Mobile App (Development)

```bash
cd frontend/web
flutter devices
flutter run -d <device-id> \
  --dart-define=AI_SERVICE_URL=http://10.0.2.2:8000 \
  --dart-define=DRUPAL_URL=http://10.0.2.2:80 \
  --dart-define=SUPERSET_URL=http://10.0.2.2:8088
```

Lưu ý endpoint theo môi trường:

- Android emulator: dùng `http://10.0.2.2:<port>` để gọi service trên host.
- iOS simulator: thường dùng được `http://localhost:<port>`.
- Thiết bị thật: dùng IP LAN của máy chạy Docker, ví dụ `http://192.168.1.10:8000`.

---

## 🐳 Docker Compose (TV3 chịu trách nhiệm file này)

```bash
# File: docker-compose.yml ở root project
docker compose up -d        # Khởi động tất cả
docker compose ps           # Xem status
docker compose logs -f ai_service   # Xem log AI service
docker compose down -v      # Dừng và xóa volumes (cẩn thận!)
```

**Services trong docker-compose.yml:**

```yaml
services:
  postgres:    # Port 5432
  neo4j:       # Port 7474, 7687
  chromadb:    # Port 8001
  redis:       # Port 6379
  rabbitmq:    # Port 5672, 15672 (management UI)
  ai_service:  # Port 8000 — build từ ai_service/Dockerfile
  drupal:      # Port 80
  superset:    # Port 8088
```

---

## 📡 Giao tiếp với AI Service (TV2)

TV3 gọi AI Service qua các endpoint đã được TV2 định nghĩa. Flutter Web và Mobile nên dùng cùng một Dart client.

```dart
// lib/services/ai_client.dart
import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;

class AiClient {
  AiClient({required this.baseUrl, required this.token});

  final String baseUrl;
  final String token;

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      };

  Future<Map<String, dynamic>> startTranslation({
    required Uint8List fileBytes,
    required String fileType,
    required String domain,
  }) async {
    final res = await http.post(
      Uri.parse('$baseUrl/translate/'),
      headers: _headers,
      body: jsonEncode({
        'file_b64': base64Encode(fileBytes),
        'file_type': fileType,
        'domain': domain,
      }),
    );

    if (res.statusCode != 202 && res.statusCode != 200) {
      throw Exception('Create translate job failed: ${res.statusCode}');
    }

    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getResult(String jobId) async {
    final res = await http.get(
      Uri.parse('$baseUrl/translate/$jobId'),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (res.statusCode != 200) {
      throw Exception('Get translate job failed: ${res.statusCode}');
    }

    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> lookupTerm(String term, String domain) async {
    final uri = Uri.parse('$baseUrl/terms/lookup').replace(
      queryParameters: {'q': term, 'domain': domain},
    );

    final res = await http.get(
      uri,
      headers: {'Authorization': 'Bearer $token'},
    );

    if (res.statusCode != 200) {
      throw Exception('Lookup term failed: ${res.statusCode}');
    }

    return jsonDecode(res.body) as Map<String, dynamic>;
  }
}
```

---

## 📊 Apache Superset Setup

```bash
# Lần đầu khởi động
docker compose exec superset superset init
docker compose exec superset superset import-dashboards \
  -p analytics/superset/dashboards/sci_translate_dashboard.json

# Truy cập: http://localhost:8088
# Login: admin / admin (đổi ngay sau lần đầu)
```

**4 charts cần tạo:**

1. `daily_translations.sql` → Line chart: Lượt dịch theo ngày
2. `bleu_score_trend.sql` → Line chart: BLEU Score trung bình theo tuần
3. `top_terms.sql` → Bar chart: Top 10 thuật ngữ được tra cứu nhiều nhất
4. `domain_distribution.sql` → Pie chart: Phân bố lĩnh vực khoa học

---

## 🧪 Chạy Tests

```bash
# Flutter unit/widget tests
cd frontend/web
flutter test

# Test riêng một widget/feature
flutter test test/features/translate/bilingual_view_test.dart

# Integration test Flutter
flutter test integration_test

# E2E test toàn hệ thống — TV1 điều phối
cd ../../tests/e2e && pytest test_web_flows.py -v
```

---

## 📋 Checklist tích hợp sau khi nhận bàn giao từ TV2 (Tuần 8)

```
[ ] docker compose up -d → tất cả services healthy
[ ] curl http://localhost:8000/health → {"status": "ok"}
[ ] Flutter web chạy được ở http://localhost:3000
[ ] Flutter mobile gọi được API theo đúng base URL của emulator/device
[ ] Test upload file PDF thật → nhận kết quả trong < 60s
[ ] Bản dịch song ngữ hiển thị đúng trên web
[ ] Thuật ngữ được highlight và tooltip hoạt động
[ ] Mobile app: dịch văn bản ngắn thành công
[ ] Superset: 4 charts hiển thị dữ liệu thực
[ ] Thông báo TV1: sẵn sàng cho integration test E2E
```

---

## ⚠️ Lưu ý quan trọng

- **Trước Tuần 8** dùng `USE_MOCK=true` — không ngồi chờ TV2.
- Flutter client không hardcode URL AI service; đọc từ `--dart-define` hoặc `.env`.
- Dùng `Uint8List` cho file input để chạy được cả Flutter Web và Mobile.
- Mọi thay đổi cấu trúc Drupal: export config bằng `drush cex`, commit file `cms/config/`.
- Dashboard Superset: export JSON và commit vào `analytics/superset/dashboards/`.
