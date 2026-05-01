# 🐳 SCI-Translate — Hướng dẫn Truy cập Docker Services

> **Cập nhật:** 01/05/2026
> **Tổng số services:** 8 (+ Ollama chạy riêng)
> **Network:** `sci_translate_network`

---

## 📋 Mục lục

0. [Quick Start — Bắt đầu lần đầu](#0-quick-start--bắt-đầu-lần-đầu)
1. [Tổng quan Services và Truy cập](#1-tổng-quan-services-và-truy-cập)
2. [Phân công theo vai trò](#2-phân-công-theo-vai-trò)
3. [Khởi động theo giai đoạn](#3-khởi-động-theo-giai-đoạn)
4. [Hướng dẫn chi tiết từng vai trò](#4-hướng-dẫn-chi-tiết-từng-vai-trò)
5. [Kiểm tra health từng service](#5-kiểm-tra-health-từng-service)
6. [Thông tin đăng nhập tập trung](#6-thông-tin-đăng-nhập-tập-trung)
7. [Lệnh Docker thường dùng](#7-lệnh-docker-thường-dùng)
8. [Xử lý sự cố](#8-xử-lý-sự-cố)

---

## 0. Quick Start — Bắt đầu lần đầu

> Dành cho thành viên mới clone repo về lần đầu

```powershell
# 1. Clone repo
git clone https://github.com/duyanhtr130905/sci-translate.git
cd sci-translate

# 2. Tạo file .env từ mẫu
cp .env.example .env
# KHÔNG cần sửa gì cho môi trường dev

# 3. Khởi động toàn bộ hệ thống
docker compose up -d

# 4. Chờ 60s rồi kiểm tra
docker compose ps -a
# Tất cả STATUS phải là "healthy" hoặc "running"

# 5. Kiểm tra AI Service
curl http://localhost:8000/health
# Kết quả mong đợi: {"status": "ok", "engine": "ollama", "model": "gemma2"}
```

> **Lưu ý Ollama (TV2):** Ollama KHÔNG chạy trong Docker.
> TV2 phải cài và chạy Ollama riêng trên máy host. Xem hướng dẫn tại mục TV2 bên dưới.

---

## 1. Tổng quan Services và Truy cập

| STT | Service | URL / Endpoint | Port | Loại truy cập |
|-----|---------|----------------|------|---------------|
| 1 | PostgreSQL | `localhost:5432` | 5432 | CLI (psql) hoặc GUI (pgAdmin, DBeaver) |
| 2 | Neo4j | http://localhost:7474 | 7474 và 7687 | Web Browser hoặc CLI (cypher-shell) |
| 3 | ChromaDB | http://localhost:8001 | 8001 | REST API |
| 4 | Redis | `localhost:6379` | 6379 | CLI (redis-cli) |
| 5 | RabbitMQ | http://localhost:15672 | 5672 và 15672 | Web UI hoặc AMQP |
| 6 | AI Service | http://localhost:8000/docs | 8000 | Swagger UI hoặc REST API |
| 7 | Drupal CMS | http://localhost:80 | 80 | Web Browser |
| 8 | Superset BI | http://localhost:8088 | 8088 | Web Browser |
| — | Ollama | http://localhost:11434 | 11434 | REST API (chạy ngoài Docker) |

---

## 2. Phân công theo vai trò

```
TV1 - Leader / BA / QA
  Giám sát toàn bộ hệ thống
  Xem báo cáo trên Superset
  Kiểm thử API và giao diện

TV2 - AI Engineer
  AI Service (chính)
  Ollama (chạy ngoài Docker)
  Neo4j - Knowledge Graph
  ChromaDB - RAG vector store
  Redis - cache và Celery backend
  RabbitMQ - task queue

TV3 - Web và Mobile Dev
  Drupal CMS (chính)
  Superset BI (chính)
  docker-compose.yml (sở hữu)
  Frontend gọi AI Service API

TV4 - Data Engineer / QA
  PostgreSQL (chính)
  Neo4j - seed KG data
  Data Pipeline ETL
  ChromaDB - import embeddings
  QA/QC review bản dịch (Tuần 10-11)
```

---

## 3. Khởi động theo giai đoạn

Không nhất thiết phải chạy tất cả 8 services cùng lúc. Mỗi thành viên chỉ cần khởi động services liên quan đến công việc của mình.

```powershell
# TV4 - Chỉ cần data services
docker compose up -d postgres neo4j

# TV2 - Cần AI services
docker compose up -d postgres neo4j chromadb redis rabbitmq
# Sau đó chạy Ollama riêng (xem mục TV2)

# TV3 - Cần CMS và BI
docker compose up -d postgres drupal superset

# TV1 / Integration - Tất cả
docker compose up -d
```

---

## 4. Hướng dẫn chi tiết từng vai trò

### TV1 — Trần Duy Anh (Leader / BA / QA)

**Nhiệm vụ Docker:**
- Giám sát toàn bộ hệ thống hoạt động ổn định
- Kiểm thử tích hợp giữa các services
- Review logs khi có lỗi, phối hợp các thành viên xử lý

**Services cần truy cập thường xuyên:**

| Service | Mục đích | Cách truy cập |
|---------|----------|---------------|
| AI Service | Kiểm thử API translate, terms lookup | http://localhost:8000/docs |
| Drupal | Kiểm thử UI, luồng người dùng | http://localhost:80 |
| Superset | Xem dashboard báo cáo | http://localhost:8088 |
| Toàn bộ | Giám sát health | `docker compose ps -a` |

**Lệnh hay dùng:**

```powershell
# Xem tổng quan nhanh
docker compose ps -a

# Xem resource usage CPU và RAM
docker stats --no-stream

# Xem logs tất cả service
docker compose logs --tail 50

# Chạy integration tests (Tuần 9)
docker compose exec ai_service pytest tests/integration/ -v

# Chạy e2e tests (Tuần 10)
docker compose exec ai_service pytest tests/e2e/ -v
```

---

### TV2 — Nguyễn Lê Ngọc Bảo (AI Engineer)

**Cài Ollama trước khi làm việc (chạy 1 lần):**

```powershell
# Linux / WSL
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Tải installer từ https://ollama.com/download/windows

# Pull model (~5.4GB, chạy 1 lần)
ollama pull gemma2

# Chạy Ollama daemon (giữ terminal này mở khi làm việc)
ollama serve
# Ollama chạy tại http://localhost:11434

# Kiểm tra
ollama list
# Phải thấy "gemma2" trong danh sách
```

**Nhiệm vụ Docker:**
- Phát triển và vận hành AI Service (FastAPI)
- Quản lý Knowledge Graph trên Neo4j
- Quản lý RAG vector store trên ChromaDB
- Cấu hình Celery workers (Redis + RabbitMQ)

**Services cần truy cập thường xuyên:**

| Service | Mục đích | Đăng nhập |
|---------|----------|-----------|
| AI Service | Develop và debug API | http://localhost:8000/docs |
| Neo4j | Quản lý Knowledge Graph | http://localhost:7474 — neo4j / N3o4jSci2026! |
| ChromaDB | Quản lý vector embeddings | http://localhost:8001/api/v1 (REST API) |
| Redis | Kiểm tra cache, Celery result | CLI bên dưới |
| RabbitMQ | Monitor task queue | http://localhost:15672 — sci_rabbit / R4bbitSci2026! |

**Lệnh hay dùng:**

```powershell
# AI Service - Rebuild sau khi thay đổi code
docker compose up -d --build ai_service

# AI Service - Xem logs real-time
docker compose logs -f ai_service

# AI Service - Vào shell container để debug
docker compose exec ai_service bash

# AI Service - Chạy unit test
docker compose exec ai_service pytest tests/ -v

# AI Service - Chạy Alembic migration
docker compose exec ai_service alembic upgrade head

# AI Service - Tạo migration mới
docker compose exec ai_service alembic revision --autogenerate -m "add_new_table"

# Neo4j - Chạy Cypher query
docker compose exec neo4j cypher-shell -u neo4j -p "N3o4jSci2026!" "MATCH (n) RETURN count(n)"

# Neo4j - Xem tất cả labels
docker compose exec neo4j cypher-shell -u neo4j -p "N3o4jSci2026!" "CALL db.labels()"

# ChromaDB - Kiểm tra heartbeat
curl http://localhost:8001/api/v1/heartbeat

# ChromaDB - Liệt kê collections
curl http://localhost:8001/api/v1/collections

# Redis - Kiểm tra keys
docker compose exec redis redis-cli -a "R3disSci2026!" KEYS "*"

# RabbitMQ - Xem queue list
docker compose exec rabbitmq rabbitmqctl list_queues
```

**Kết nối từ code ai_service (trong container):**

```python
# PostgreSQL
DATABASE_URL = "postgresql://sci_user:SciTr4nsl8te2026!@postgres:5432/sci_translate"

# Neo4j
NEO4J_URI = "bolt://neo4j:7687"

# ChromaDB
CHROMADB_HOST = "chromadb"

# Redis
REDIS_URL = "redis://:R3disSci2026!@redis:6379/0"

# RabbitMQ (Celery broker)
CELERY_BROKER_URL = "amqp://sci_rabbit:R4bbitSci2026!@rabbitmq:5672/"

# Ollama (chạy trên host, KHÔNG trong Docker)
OLLAMA_BASE_URL = "http://host.docker.internal:11434"
```

---

### TV3 — Lê Huy Anh Dũng (Web và Mobile Dev)

**Nhiệm vụ Docker:**
- Sở hữu file `docker-compose.yml`, chịu trách nhiệm cập nhật khi cần
- Vận hành và cấu hình Drupal CMS
- Vận hành và cấu hình Superset BI
- Tích hợp Frontend gọi API từ AI Service

**Services cần truy cập thường xuyên:**

| Service | Mục đích | Đăng nhập |
|---------|----------|-----------|
| Drupal CMS | Quản lý nội dung, cấu hình modules | http://localhost:80 |
| Superset | Tạo dashboards, charts | http://localhost:8088 — admin / Admin2026! |
| AI Service | Test API endpoints từ Frontend | http://localhost:8000/docs |

**Lệnh hay dùng:**

```powershell
# Drupal - Cài module mới
docker compose exec drupal composer require drupal/jsonapi_extras

# Drupal - Clear cache
docker compose exec drupal drush cr

# Drupal - Export config (commit lên git sau khi export)
docker compose exec drupal drush cex
git add cms/config/
git commit -m "config: export Drupal config"

# Drupal - Xem logs
docker compose logs -f drupal

# Superset - Reset admin password
docker compose exec superset superset fab reset-password --username admin --password NewPassword123

# Superset - Import dashboard
docker compose exec superset superset import-dashboards -p analytics/superset/dashboards/sci_translate_dashboard.json
```

**Drupal — Cấu hình lần đầu:**

1. Mở http://localhost:80
2. Chọn ngôn ngữ: **English**
3. Chọn profile: **Standard**
4. Nhập Database configuration:
   - Type: **PostgreSQL**
   - Database name: `drupal`
   - Username: `sci_user`
   - Password: `SciTr4nsl8te2026!`
   - Host: `postgres` (KHÔNG phải localhost)
   - Port: `5432`
5. Hoàn tất setup wizard

**Superset — Kết nối Data Source:**

1. Mở http://localhost:8088, login `admin` / `Admin2026!`
2. Vào **Settings** > **Database Connections** > **+ Database**
3. Chọn **PostgreSQL**
4. Nhập SQLAlchemy URI:
   ```
   postgresql://sci_user:SciTr4nsl8te2026!@postgres:5432/sci_translate
   ```
5. Test Connection > Save

---

### TV4 — Phạm Dương Hoàng (Data Engineer / QA)

**Nhiệm vụ Docker:**
- Quản lý schema PostgreSQL (migrations, seeds)
- Chạy Data Pipeline ETL
- Import Knowledge Graph data vào Neo4j
- QA/QC review bản dịch (Tuần 10-11)

**Services cần truy cập thường xuyên:**

| Service | Mục đích | Đăng nhập |
|---------|----------|-----------|
| PostgreSQL | Schema, migration, seed data | CLI hoặc DBeaver |
| Neo4j | Import thuật ngữ KG | http://localhost:7474 — neo4j / N3o4jSci2026! |
| ChromaDB | Import corpus embeddings | REST API http://localhost:8001 |
| RabbitMQ | Monitor ETL pipeline tasks | http://localhost:15672 |

**Lệnh hay dùng:**

```powershell
# PostgreSQL - Truy cập interactive
docker compose exec postgres psql -U sci_user -d sci_translate

# PostgreSQL - Xem tất cả tables
docker compose exec postgres psql -U sci_user -d sci_translate -c "\dt"

# PostgreSQL - Chạy SQL file
Get-Content database/migrations/001_init.sql | docker compose exec -T postgres psql -U sci_user -d sci_translate

# PostgreSQL - Backup database
docker compose exec postgres pg_dump -U sci_user sci_translate > backup_$(Get-Date -Format "yyyyMMdd").sql

# Neo4j - Đếm nodes
docker compose exec neo4j cypher-shell -u neo4j -p "N3o4jSci2026!" "MATCH (n) RETURN labels(n), count(n)"

# ChromaDB - Kiểm tra collections
curl http://localhost:8001/api/v1/collections

# QA/QC (Tuần 10-11) - Lấy 50 bản dịch để review
curl http://localhost:8000/translate/batch-sample?n=50 > qa_samples.json
```

**Kết nối PostgreSQL từ DBeaver hoặc pgAdmin:**

| Field | Value |
|-------|-------|
| Host | `localhost` |
| Port | `5432` |
| Database | `sci_translate` |
| Username | `sci_user` |
| Password | `SciTr4nsl8te2026!` |

---

## 5. Kiểm tra health từng service

```powershell
# PostgreSQL
docker compose exec postgres pg_isready -U sci_user
# Mong đợi: localhost:5432 - accepting connections

# Neo4j
curl http://localhost:7474
# Mong đợi: 200 OK

# ChromaDB
curl http://localhost:8001/api/v1/heartbeat
# Mong đợi: {"nanosecond heartbeat":...}

# Redis
docker compose exec redis redis-cli -a "R3disSci2026!" ping
# Mong đợi: PONG

# RabbitMQ
curl http://localhost:15672
# Mong đợi: 200 OK

# AI Service
curl http://localhost:8000/health
# Mong đợi: {"status": "ok", "engine": "ollama"}

# Ollama (chạy ngoài Docker)
curl http://localhost:11434
# Mong đợi: "Ollama is running"

# Drupal
curl http://localhost:80
# Mong đợi: 200 OK

# Superset
curl http://localhost:8088/health
# Mong đợi: "OK"
```

---

## 6. Thông tin đăng nhập tập trung

> **CẢNH BÁO:** Credentials này chỉ dùng cho môi trường **development**.
> KHÔNG dùng cho production. KHÔNG commit file `.env` lên git.

### Web UI Logins

| Service | URL | Username | Password |
|---------|-----|----------|----------|
| Neo4j Browser | http://localhost:7474 | `neo4j` | `N3o4jSci2026!` |
| RabbitMQ Mgmt | http://localhost:15672 | `sci_rabbit` | `R4bbitSci2026!` |
| Superset BI | http://localhost:8088 | `admin` | `Admin2026!` |
| Drupal CMS | http://localhost:80 | setup wizard lần đầu | — |
| AI Swagger | http://localhost:8000/docs | không cần login | — |

### Database / Infra Logins

| Service | Connection | Username | Password |
|---------|-----------|----------|----------|
| PostgreSQL | `localhost:5432/sci_translate` | `sci_user` | `SciTr4nsl8te2026!` |
| Redis | `localhost:6379` | — | `R3disSci2026!` |
| RabbitMQ | `localhost:5672` | `sci_rabbit` | `R4bbitSci2026!` |
| Neo4j | `bolt://localhost:7687` | `neo4j` | `N3o4jSci2026!` |
| ChromaDB | `http://localhost:8001` | — | không auth |
| Ollama | `http://localhost:11434` | — | không auth |

---

## 7. Lệnh Docker thường dùng

```powershell
# Khởi động tất cả
docker compose up -d

# Dừng tất cả (GIỮ data)
docker compose down

# Xem trạng thái
docker compose ps -a

# Xem resource usage
docker stats --no-stream

# Xem logs tất cả
docker compose logs --tail 50

# Xem logs 1 service
docker compose logs -f <service_name>

# Restart 1 service
docker compose restart <service_name>

# Rebuild 1 service sau khi sửa code
docker compose up -d --build <service_name>

# Vào shell container
docker compose exec <service_name> bash
```

**Tên service hợp lệ:**
```
postgres | neo4j | chromadb | redis | rabbitmq | ai_service | drupal | superset
```

---

## 8. Xử lý sự cố

### Service không khởi động

```powershell
# 1. Xem logs lỗi
docker compose logs <service_name> --tail 100

# 2. Restart service
docker compose restart <service_name>

# 3. Force recreate
docker compose up -d --force-recreate <service_name>

# 4. Nuclear option - XÓA DATA - cẩn thận!
docker compose down
docker volume rm sci_translate_<service>_data
docker compose up -d
```

### Port bị chiếm

```powershell
# Tìm process chiếm port (ví dụ 5432)
netstat -ano | findstr :5432

# Đổi port trong .env
# POSTGRES_PORT=5433
```

### Ai liên hệ khi service lỗi?

| Service bị lỗi | Liên hệ | Ghi chú |
|----------------|----------|---------|
| `postgres` | TV4 — Phạm Dương Hoàng | Schema, data issues |
| `neo4j` | TV2 — Nguyễn Lê Ngọc Bảo | KG data, queries |
| `chromadb` | TV2 — Nguyễn Lê Ngọc Bảo | Vector store issues |
| `redis` | TV2 — Nguyễn Lê Ngọc Bảo | Cache, Celery issues |
| `rabbitmq` | TV2 — Nguyễn Lê Ngọc Bảo | Task queue issues |
| `ai_service` | TV2 — Nguyễn Lê Ngọc Bảo | API, model issues |
| `drupal` | TV3 — Lê Huy Anh Dũng | CMS, web issues |
| `superset` | TV3 — Lê Huy Anh Dũng | Dashboard, BI issues |
| `docker-compose.yml` | TV3 — Lê Huy Anh Dũng | Infrastructure config |
| Tất cả / không rõ | TV1 — Trần Duy Anh | Escalation, coordination |

---

> **Ghi nhớ:** Mọi thay đổi credentials phải cập nhật đồng thời trong file `.env` VÀ file này.