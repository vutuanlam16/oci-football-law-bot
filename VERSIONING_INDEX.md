# Versioning Documentation Index

Tài liệu về **Version Control System** được chia thành 3 documents theo mục đích sử dụng.

---

## 📖 Documentation Roadmap

```
┌─────────────────────────────────────────────────────────────┐
│  Bắt đầu: VERSIONING_QUICK_START.md (5 phút)                │
│  → Hiểu cơ bản, bắt đầu dùng ngay                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        v                               v
┌──────────────────┐          ┌──────────────────────┐
│ VERSION_CONTROL  │          │ VERSIONING_INTERNALS │
│ .md              │          │ .md                  │
│                  │          │                      │
│ User guide       │          │ Developer guide      │
│ Full examples    │          │ Implementation       │
│ API reference    │          │ Code walkthrough     │
└──────────────────┘          └──────────────────────┘
```

---

## 1. Quick Start Guide (Bắt đầu nhanh)

**File:** [VERSIONING_QUICK_START.md](VERSIONING_QUICK_START.md)

**Dành cho:** Mọi người (admins, users, developers)

**Thời gian đọc:** ~5 phút

**Nội dung:**
- TL;DR: Version control là gì?
- Bắt đầu nhanh (migrate, check conflicts, ingest, archive)
- 3 use cases chính
- API endpoints cơ bản
- Troubleshooting
- Best practices
- FAQ

**Khi nào đọc:**
- ✅ Bạn mới tìm hiểu về versioning system
- ✅ Bạn cần setup nhanh
- ✅ Bạn cần reference nhanh (cheat sheet)

---

## 2. User Guide (Hướng dẫn đầy đủ)

**File:** [VERSION_CONTROL.md](VERSION_CONTROL.md)

**Dành cho:** Admins, power users, researchers

**Thời gian đọc:** ~30 phút

**Nội dung:**
- Tính năng chính (version tracking, conflict detection, historical queries)
- **Kiến trúc & Cơ chế hoạt động** (chi tiết)
  - Tại sao cần version control?
  - Cách versioning hoạt động (version schema, relationships, lifecycle)
  - Cách conflict detection hoạt động (algorithm, tại sao conflicts nguy hiểm)
  - Conflict resolution strategies
- Database schema
- Migration guide
- API endpoints đầy đủ (với curl examples)
- Chat/Search với version control
- Workflow quản lý versions
- **5 Use Cases chi tiết:**
  1. Luật mới ban hành hàng năm
  2. Sửa đổi, bổ sung trong năm (minor updates)
  3. Phát hiện và xử lý conflicts
  4. Chuyển tiếp giữa các phiên bản (transition period)
  5. Research lịch sử pháp luật
- **Advanced Topics:**
  - Performance considerations
  - Edge cases & handling
  - Data migration strategies
  - Monitoring & alerting
- Best practices
- Troubleshooting
- Examples timeline

**Khi nào đọc:**
- ✅ Bạn đã đọc Quick Start và muốn hiểu sâu
- ✅ Bạn quản trị system (admin)
- ✅ Bạn cần xử lý use cases phức tạp
- ✅ Bạn cần optimize performance
- ✅ Bạn cần migrate data hiện tại

---

## 3. Developer Guide (Tài liệu kỹ thuật)

**File:** [VERSIONING_INTERNALS.md](VERSIONING_INTERNALS.md)

**Dành cho:** Developers, contributors

**Thời gian đọc:** ~45 phút

**Nội dung:**
- Architecture overview
- **Code walkthrough:**
  - Database models (Document, version fields, relationships)
  - Service layer (VersioningService methods)
  - API layer (endpoints implementation)
  - Migration scripts
- Design decisions (Q&A format)
  - Tại sao dùng version_major/minor riêng?
  - Tại sao self-referencing FK?
  - Tại sao service commits instead of caller?
  - Tại sao string strategy instead of Strategy pattern?
- Algorithm analysis (time/space complexity)
- Testing strategy (unit, integration, performance tests)
- Future improvements
- Common pitfalls
- Debugging tips
- References

**Khi nào đọc:**
- ✅ Bạn cần maintain/extend versioning system
- ✅ Bạn cần contribute code
- ✅ Bạn cần hiểu implementation details
- ✅ Bạn cần optimize hoặc debug

---

## Reading Path (Lộ trình đọc)

### Path 1: User/Admin (Không code)

```
1. VERSIONING_QUICK_START.md (5 min)
   ↓
2. Thử setup và test
   ↓
3. VERSION_CONTROL.md (30 min)
   - Skip "Kiến trúc & Cơ chế hoạt động" nếu không quan tâm
   - Đọc kỹ "Use Cases chi tiết"
   - Đọc "Best Practices"
```

**Total time:** ~35-40 minutes

### Path 2: Developer (Cần code)

```
1. VERSIONING_QUICK_START.md (5 min)
   ↓
2. VERSION_CONTROL.md - Đọc toàn bộ (30 min)
   - Chú trọng "Kiến trúc & Cơ chế hoạt động"
   - Chú trọng "Advanced Topics"
   ↓
3. VERSIONING_INTERNALS.md (45 min)
   - Code walkthrough
   - Design decisions
   - Testing strategy
```

**Total time:** ~80 minutes

### Path 3: Quick Reference (Đã biết, cần recall)

```
1. VERSIONING_QUICK_START.md - Chỉ đọc phần cần
   - Troubleshooting
   - API endpoints
   - Best practices
```

**Total time:** ~2-3 minutes

---

## Feature Comparison Table

| Feature | Quick Start | User Guide | Developer Guide |
|---------|-------------|------------|-----------------|
| TL;DR overview | ✅ | ✅ | ✅ |
| Setup steps | ✅ | ✅ | - |
| Basic API usage | ✅ | ✅✅ | ✅ |
| Architecture explanation | - | ✅✅ | ✅✅✅ |
| Use case examples | ✅ (3) | ✅✅ (5) | - |
| Advanced topics | - | ✅✅ | ✅✅✅ |
| Code implementation | - | - | ✅✅✅ |
| Design decisions | - | ✅ | ✅✅✅ |
| Testing guide | - | - | ✅✅ |
| Troubleshooting | ✅ | ✅✅ | ✅✅✅ |
| Best practices | ✅ | ✅✅ | ✅✅ |

Legend: ✅ (basic), ✅✅ (detailed), ✅✅✅ (comprehensive)

---

## External Resources

### Related Files in Project

- `app/models.py` - Document model definition
- `app/rag/versioning.py` - VersioningService implementation
- `app/schemas.py` - Pydantic schemas for version APIs
- `app/main.py` - API endpoints
- `alembic/versions/0002_add_versioning.py` - Database migration

### SQLAlchemy Documentation

- [Self-Referential Relationships](https://docs.sqlalchemy.org/en/20/orm/self_referential.html)
- [Relationship Patterns](https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html)

### FastAPI Documentation

- [Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [Response Models](https://fastapi.tiangolo.com/tutorial/response-model/)

---

## FAQ Meta (About Documentation)

**Q: Tôi nên đọc tài liệu nào trước?**

A: **VERSIONING_QUICK_START.md** → Bắt đầu ở đây, luôn luôn!

**Q: Tôi không phải developer, có cần đọc VERSIONING_INTERNALS.md không?**

A: **Không.** Đọc Quick Start + User Guide là đủ.

**Q: Tôi đã biết hết rồi, cần reference nhanh?**

A: **VERSIONING_QUICK_START.md** - Phần "API Endpoints cơ bản" và "Troubleshooting".

**Q: Các documents có duplicate content không?**

A: **Có một chút**, nhưng intentional:
- Quick Start: Breadth (rộng, nông)
- User Guide: Depth on usage (sâu về cách dùng)
- Developer Guide: Depth on implementation (sâu về implementation)

**Q: Tôi cần contribute code, đọc tài liệu nào?**

A: **Tất cả 3**, theo thứ tự:
1. Quick Start → Hiểu use cases
2. User Guide → Hiểu requirements và behavior
3. Developer Guide → Hiểu implementation để modify

---

## Feedback & Contribution

Nếu bạn thấy tài liệu:
- ❓ **Khó hiểu**: Mở issue để suggest improvements
- 🐛 **Có lỗi**: Mở PR để fix
- 📝 **Thiếu nội dung**: Mở issue để discuss additions

**Document Maintainer:** Development Team  
**Last Updated:** 2026-03-03  
**Version:** 1.0

---

## Quick Links

- 🚀 [Quick Start](VERSIONING_QUICK_START.md)
- 📖 [User Guide](VERSION_CONTROL.md)
- 💻 [Developer Guide](VERSIONING_INTERNALS.md)
- 📊 [4-Slide Presentation](VERSIONING_SLIDES_4.md) - Nội dung trình bày 3 phút
- 🏠 [Main README](README.md)
