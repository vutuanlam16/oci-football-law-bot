# Version Control - Quick Start Guide

**5 phút để hiểu và bắt đầu dùng versioning system.**

---

## TL;DR

Hệ thống quản lý **nhiều phiên bản** của cùng một luật (2023, 2024, 2025...) với:
- ✅ Version tracking (major.minor)
- ✅ Conflict detection (phát hiện nhiều versions active)
- ✅ Historical queries (tra cứu luật tại thời điểm quá khứ)
- ✅ Auto-archive versions cũ

---

## Bắt đầu nhanh

### Bước 1: Migrate database
```bash
docker compose exec app alembic upgrade head
```

### Bước 2: Kiểm tra conflicts hiện tại
```bash
curl http://localhost:8000/api/versions/conflicts
```

Nếu có conflicts → Xử lý trước khi tiếp tục.

### Bước 3: Ingest luật mới với version metadata

```bash
python scripts/ingest_folder.py data/laws_2024/ \
  --doc-id luat_bong_da_v2024.0 \
  --doc-type laws \
  --version-major 2024 \
  --version-minor 0 \
  --effective-date 2024-01-01
```

### Bước 4: Archive luật cũ

```bash
curl -X POST http://localhost:8000/api/versions/archive \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "luat_bong_da_v2023.0",
    "superseded_by_doc_id": "luat_bong_da_v2024.0"
  }'
```

**Xong!** Luật 2024 active, luật 2023 archived.

---

## 3 Use Cases chính

### 1. Luật mới hàng năm

```
Timeline:
2023-01-01: Luật 2023 có hiệu lực
2024-01-01: Luật 2024 ra đời → Archive 2023
2025-01-01: Luật 2025 ra đời → Archive 2024
```

**Workflow:**
1. Ingest luật mới → `luat_v2024.0`
2. Archive luật cũ → `luat_v2023.0`
3. User query → Chỉ tìm trong 2024 (active)

### 2. Sửa đổi trong năm

```
2024.0 (01/01): Ban hành
2024.1 (15/06): Sửa Điều 11
2024.2 (01/12): Bổ sung Điều 17
```

**Workflow:**
1. Ingest v2024.1 → Minor version
2. Archive v2024.0
3. Historical query: "Luật tháng 3/2024" → Trả về v2024.0

### 3. Nghiên cứu lịch sử

```bash
# So sánh luật 2023 vs 2024
curl -X POST http://localhost:8000/chat \
  -d '{"message":"Việt vị?","effective_on":"2023-06-01"}'

curl -X POST http://localhost:8000/chat \
  -d '{"message":"Việt vị?","effective_on":"2024-06-01"}'
```

---

## API Endpoints cơ bản

| Endpoint | Mục đích | Example |
|----------|----------|---------|
| `GET /api/versions/conflicts` | Phát hiện conflicts | `curl localhost:8000/api/versions/conflicts` |
| `GET /api/versions/stats` | Thống kê versions | `curl localhost:8000/api/versions/stats` |
| `POST /api/versions/archive` | Archive version | `curl -X POST ... -d '{"doc_id":"v2023"}'` |
| `POST /api/versions/resolve` | Auto-resolve conflicts | `curl -X POST ... -d '{"strategy":"keep_latest"}'` |

---

## Chat với Version Control

### Chỉ tìm active versions (mặc định)
```bash
curl -X POST http://localhost:8000/chat \
  -d '{"message":"Việt vị?","active_only":true}'
```
→ Chỉ trả lời từ luật hiện tại

### Tìm luật tại thời điểm quá khứ
```bash
curl -X POST http://localhost:8000/chat \
  -d '{"message":"Việt vị năm 2023?","effective_on":"2023-06-01"}'
```
→ Trả lời từ luật có hiệu lực vào 2023-06-01

### Warning khi có conflict
```json
{
  "answer": "...",
  "version_warning": "⚠️ Phát hiện 2 xung đột phiên bản..."
}
```
→ System cảnh báo khi detect conflict

---

## Naming Convention

**Document ID:**
```
{base_name}_v{major}.{minor}
```

**Examples:**
- `luat_bong_da_v2023.0` ✅
- `luat_bong_da_v2024.1` ✅
- `luat_ky_luat_v2023.0` ✅
- `luat_bong_da_2024` ❌ (thiếu version)

**Title:**
```
LUẬT THI ĐẤU BÓNG ĐÁ (2024)
```

---

## Troubleshooting

### Lỗi: "Phát hiện 2 xung đột phiên bản"

**Nguyên nhân:** Có ≥2 documents active của cùng một luật.

**Xử lý:**
```bash
# Option 1: Auto-resolve
curl -X POST http://localhost:8000/api/versions/resolve \
  -d '{"strategy":"keep_latest"}'

# Option 2: Manual archive
curl -X POST http://localhost:8000/api/versions/archive \
  -d '{"doc_id":"luat_v2023.0"}'
```

### Câu trả lời sai/mâu thuẫn

**Nguyên nhân:** System retrieval từ nhiều versions khác nhau.

**Kiểm tra:**
```bash
curl http://localhost:8000/api/versions/conflicts
```

Nếu có conflicts → Resolve ngay.

### Historical query không hoạt động

**Nguyên nhân:** Documents không có `effective_date`.

**Xử lý:** Update metadata cho documents:
```python
doc.effective_date = date(2024, 1, 1)
db.commit()
```

---

## Best Practices

### ✅ DO

1. **Luôn set effective_date** khi ingest
2. **Archive version cũ** ngay sau khi ingest mới
3. **Check conflicts định kỳ** (hàng tuần)
4. **Dùng naming convention** nhất quán
5. **Test historical queries** sau khi ingest

### ❌ DON'T

1. **Không** để nhiều versions active cùng lúc (trừ transition period)
2. **Không** xóa documents (dùng archive)
3. **Không** thay đổi `doc_id` sau khi ingest
4. **Không** dùng version_major/minor tùy tiện

---

## Next Steps

**Đọc chi tiết:**
- [VERSION_CONTROL.md](VERSION_CONTROL.md) - Full documentation với examples
- [VERSIONING_INTERNALS.md](VERSIONING_INTERNALS.md) - Implementation details cho developers

**Common tasks:**
- [Ingest luật mới](#bắt-đầu-nhanh)
- [Xử lý conflicts](#troubleshooting)
- [Historical queries](#chat-với-version-control)

---

## FAQ

**Q: Version_major nên dùng năm (2024) hay số thứ tự (1, 2, 3)?**

A: Khuyến nghị dùng **năm** (2024, 2025) vì:
- Dễ hiểu (human-readable)
- Sortable
- Match với cách gọi thực tế ("Luật 2024")

**Q: Khi nào cần tạo minor version (x.1, x.2)?**

A: Khi có **sửa đổi nhỏ** trong năm:
- Sửa 1-2 điều luật
- Bổ sung điều khoản
- Errata/corrections

**Q: Có thể có 2 versions active cùng lúc không?**

A: **Tránh** nếu có thể. Chỉ cho phép trong **transition period** (được công bố nhưng chưa hiệu lực). Nếu có, nên dùng `effective_date` để filter.

**Q: Archive hay delete documents cũ?**

A: Luôn **archive** (set `is_active=false`), không delete. Lý do:
- Giữ lại lịch sử
- Support historical queries
- Audit trail

**Q: Làm sao biết version nào được dùng để trả lời user?**

A: Check `citations` trong response:
```json
{
  "citations": [
    {
      "doc_title": "LUẬT BÓNG ĐÁ (2024)",
      "version": "2024.0",
      ...
    }
  ]
}
```

---

**Thời gian đọc:** ~5 phút  
**Last updated:** 2026-03-03
