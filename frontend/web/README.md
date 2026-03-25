# Frontend & CMS & BI — TV3 (Web & Mobile Developer)

> **Người phụ trách:** TV3  
> **Stack:** React 18 · React Native · Drupal 10 · Apache Superset · Docker  
> **Phụ thuộc:** AI Service của TV2 (Tuần 8 mới có API)

---

## 📁 Cấu trúc thư mục

```
frontend/
├── web/                         ← React.js Web App
│   ├── src/
│   │   ├── components/
│   │   │   ├── TranslateForm/   ← Upload file + chọn domain
│   │   │   ├── BilingualView/   ← Hiển thị song ngữ + highlight thuật ngữ
│   │   │   ├── TermTooltip/     ← Tooltip tra cứu thuật ngữ KG
│   │   │   ├── ReviewPanel/     ← QA Review interface
│   │   │   └── Dashboard/       ← Link đến Superset
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx
│   │   │   ├── TranslatePage.jsx   ← Trang dịch chính
│   │   │   ├── HistoryPage.jsx     ← Lịch sử dịch
│   │   │   ├── TermsPage.jsx       ← Tra cứu thuật ngữ
│   │   │   └── ReviewPage.jsx      ← QA review (chỉ Reviewer)
│   │   ├── hooks/
│   │   │   ├── useTranslate.js  ← Poll job_id cho đến khi completed
│   │   │   └── useAuth.js       ← JWT token management
│   │   ├── api/
│   │   │   ├── aiClient.js      ← Gọi AI Service (localhost:8000)
│   │   │   └── drupalClient.js  ← Gọi Drupal REST API (localhost:80)
│   │   └── App.jsx
│   ├── public/
│   ├── package.json
│   └── README.md
│
└── mobile/                      ← React Native / Flutter
    ├── src/
    │   ├── screens/
    │   │   ├── HomeScreen.jsx   ← Tab: Dịch nhanh
    │   │   ├── HistoryScreen.jsx
    │   │   └── TermsScreen.jsx
    │   ├── components/
    │   └── services/
    │       └── api.js           ← Dùng chung endpoint với web
    ├── package.json
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

## 🚀 Chạy Web App (Development)

```bash
cd frontend/web
npm install
npm start
# → http://localhost:3000
```

**Cấu hình API endpoints (file `.env.local`):**
```env
REACT_APP_AI_SERVICE_URL=http://localhost:8000
REACT_APP_DRUPAL_URL=http://localhost:80
REACT_APP_SUPERSET_URL=http://localhost:8088
```

**⚠️ Trước Tuần 8 (chưa có AI Service):** Dùng mock data:
```bash
# Bật mock mode
REACT_APP_USE_MOCK=true npm start
# Mock data nằm ở: src/api/__mocks__/
```

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

TV3 gọi AI Service qua các endpoint đã được TV2 định nghĩa:

```javascript
// src/api/aiClient.js

// 1. Gửi file để dịch
const startTranslation = async (file, domain) => {
  const b64 = await fileToBase64(file)
  const res = await fetch(`${AI_URL}/translate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ file_b64: b64, file_type: file.name.split('.').pop(), domain })
  })
  return res.json()  // { job_id, status, estimated_seconds }
}

// 2. Poll kết quả (dùng hook useTranslate.js)
const getResult = async (jobId) => {
  const res = await fetch(`${AI_URL}/translate/${jobId}`)
  return res.json()  // { status, result: { segments, bleu_score } }
}

// 3. Tra thuật ngữ
const lookupTerm = async (term, domain) => {
  const res = await fetch(`${AI_URL}/terms/lookup?q=${term}&domain=${domain}`)
  return res.json()
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
# Web unit tests
cd frontend/web && npm test

# Component tests
npm test -- --testPathPattern=BilingualView

# E2E test (cần toàn bộ hệ thống chạy) — TV1 điều phối
cd tests/e2e && pytest test_web_flows.py -v
```

---

## 📋 Checklist tích hợp sau khi nhận bàn giao từ TV2 (Tuần 8)

```
[ ] docker compose up -d → tất cả services healthy
[ ] curl http://localhost:8000/health → {"status": "ok"}
[ ] Test upload file PDF thật → nhận kết quả trong < 60s
[ ] Bản dịch song ngữ hiển thị đúng trên web
[ ] Thuật ngữ được highlight và tooltip hoạt động
[ ] Mobile app: dịch văn bản ngắn thành công
[ ] Superset: 4 charts hiển thị dữ liệu thực
[ ] Thông báo TV1: sẵn sàng cho integration test E2E
```

---

## ⚠️ Lưu ý quan trọng

- **Trước Tuần 8** dùng `REACT_APP_USE_MOCK=true` — không ngồi chờ TV2
- Mọi thay đổi cấu trúc Drupal: export config bằng `drush cex`, commit file `cms/config/`
- Dashboard Superset: export JSON và commit vào `analytics/superset/dashboards/`
- **KHÔNG hardcode** URL AI service — dùng biến môi trường trong `.env.local`
