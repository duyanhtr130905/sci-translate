# Contract: TV4 (Data) → TV2 (AI)
# Tuần bàn giao: Tuần 6

## TV4 cam kết cung cấp

| Item | Path | Format | Min size |
|---|---|---|---|
| Corpus train | `data_pipeline/corpus/train.tsv` | UTF-8, EN\\tVI | 50,000 dòng |
| Corpus test | `data_pipeline/corpus/test.tsv` | UTF-8, EN\\tVI | 5,000 dòng |
| DB migration | Alembic tới `head` | SQL | - |
| KG seed | Neo4j nodes + edges | Cypher đã chạy | 500+ nodes |

## TV2 cam kết kiểm tra

Chạy `pytest data_pipeline/tests/ -v` → tất cả PASS trong vòng 24h sau bàn giao.

## Xác nhận

TV4 tạo issue: `[Handoff] TV4→TV2 complete - Week 6`  
TV2 comment: `✅ Verified - <date>`  
TV1 close issue sau khi cả 2 xác nhận.
