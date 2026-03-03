# Versioning System - Internal Documentation

## Dành cho Developers

Document này giải thích chi tiết **implementation** của versioning system trong codebase. Nếu bạn muốn hiểu cách sử dụng, xem [VERSION_CONTROL.md](VERSION_CONTROL.md).

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     API Layer (main.py)                      │
│  /api/versions/conflicts, /api/versions/archive, etc.       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│              Service Layer (versioning.py)                   │
│  VersioningService: detect_conflicts(), archive_version()   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│                 ORM Layer (models.py)                        │
│  Document model with version fields & relationships         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│              Database (PostgreSQL)                           │
│  documents table with version columns & indexes             │
└─────────────────────────────────────────────────────────────┘
```

**Design Philosophy:**
- **Separation of Concerns**: Business logic trong service layer, API chỉ handle HTTP
- **Single Responsibility**: Mỗi method trong VersioningService làm 1 việc rõ ràng
- **Stateless Service**: VersioningService không cache state, luôn query fresh data
- **Explicit is better than implicit**: Không có magic, mọi operations phải được gọi rõ ràng

---

## Code Walkthrough

### 1. Database Models (`app/models.py`)

#### Document Model - Version Fields

```python
class Document(Base):
    __tablename__ = "documents"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    
    # Version control fields
    version_major: Mapped[int] = mapped_column(Integer, default=1, server_default="1", index=True)
    version_minor: Mapped[int] = mapped_column(Integer, default=0, server_default="0", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", index=True)
    effective_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    archived_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    superseded_by_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    
    # Relationships
    superseded_by: Mapped["Document | None"] = relationship("Document", remote_side=[id], foreign_keys=[superseded_by_id])
```

**Key Design Decisions:**

**Q: Tại sao dùng `version_major` và `version_minor` riêng lẻ thay vì 1 field `version` string?**

A: 
- ✅ **Sortable**: Có thể ORDER BY version_major DESC, version_minor DESC
- ✅ **Queryable**: WHERE version_major = 2024
- ✅ **Type-safe**: Integer thay vì string parsing
- ❌ String "2024.1" khó so sánh ("2024.10" > "2024.2" nếu sort alphabetically)

**Q: Tại sao cần cả `is_active` và `archived_at`?**

A:
- `is_active`: **Query filter** (binary: active or not) → Fast index scan
- `archived_at`: **Audit trail** (when was it archived?) → Timestamp for history

**Q: Tại sao `superseded_by_id` nullable?**

A: Có 2 scenarios archive mà không có superseding document:
1. Luật bị hủy bỏ hoàn toàn (không có version thay thế)
2. Archive tạm thời (chưa biết version mới)

**Q: Tại sao dùng self-referencing FK thay vì separate table `version_history`?**

A:
- ✅ **Simplicity**: Không cần join thêm table
- ✅ **Integrity**: DB enforces relationship
- ❌ **Trade-off**: Chỉ track 1-to-1 superseding (không track many-to-one merge scenarios)

#### Relationship Details

```python
superseded_by: Mapped["Document | None"] = relationship(
    "Document", 
    remote_side=[id],  # Chỉ định remote side (để SQLAlchemy biết direction)
    foreign_keys=[superseded_by_id]  # Explicit FK (vì self-referencing)
)
```

**Usage:**
```python
doc = db.query(Document).filter_by(doc_id="luat_v2023.0").first()

# Get document that supersedes this one
if doc.superseded_by:
    print(f"Superseded by: {doc.superseded_by.doc_id}")

# Get documents superseded by this one (reverse relationship)
# Note: Cần define reverse relationship nếu muốn query ngược chiều
```

**Limitation:** Current model chỉ support **one-to-one** superseding. Không support:
- **Many-to-one**: 2 luật merge thành 1
- **One-to-many**: 1 luật split thành 2

Nếu cần support, phải tách thành bảng riêng:
```sql
CREATE TABLE version_relationships (
  from_document_id INT REFERENCES documents(id),
  to_document_id INT REFERENCES documents(id),
  relationship_type VARCHAR(50),  -- supersedes|merges_into|splits_into
  PRIMARY KEY (from_document_id, to_document_id)
);
```

---

### 2. Service Layer (`app/rag/versioning.py`)

#### VersioningService Class

```python
class VersioningService:
    def __init__(self, db: Session):
        self.db = db
```

**Design Choice: Why pass `db` to constructor instead of global?**

A:
- ✅ **Testability**: Easy to mock database in unit tests
- ✅ **Thread-safety**: Each request gets own session
- ✅ **Explicit dependencies**: Clear what service needs
- ❌ Global session → Hard to test, potential race conditions

#### detect_conflicts() - Deep Dive

**Full Implementation:**
```python
def detect_conflicts(
    self, 
    doc_type: Optional[str] = None,
    effective_on: Optional[date] = None
) -> list[dict]:
    # Step 1: Query active documents
    query = self.db.query(Document).filter(Document.is_active == True)
    
    if doc_type:
        query = query.filter(Document.doc_type == doc_type)
    
    if effective_on:
        query = query.filter(
            or_(
                Document.effective_date.is_(None),
                Document.effective_date <= effective_on
            )
        )
    
    docs = query.all()
    
    # Step 2: Group by base identifier
    groups = {}
    for doc in docs:
        # Extract base_id (remove version suffix)
        base_id = doc.doc_id.split("_v")[0] if "_v" in doc.doc_id else doc.doc_id
        
        # Extract title key (remove year in parentheses)
        title_key = doc.title.split("(")[0].strip() if "(" in doc.title else doc.title.strip()
        
        # Grouping key: (base_id, title, doc_type)
        key = (base_id, title_key, doc.doc_type)
        
        if key not in groups:
            groups[key] = []
        
        groups[key].append({
            "doc_id": doc.doc_id,
            "id": doc.id,
            "title": doc.title,
            "version": f"{doc.version_major}.{doc.version_minor}",
            "version_major": doc.version_major,
            "version_minor": doc.version_minor,
            "effective_date": doc.effective_date,
            "created_at": doc.created_at,
        })
    
    # Step 3: Find groups with multiple versions (conflicts)
    conflicts = []
    for (base_id, title_key, doc_type), versions in groups.items():
        if len(versions) > 1:
            conflicts.append({
                "base_doc": base_id,
                "title_pattern": title_key,
                "doc_type": doc_type,
                "conflict_count": len(versions),
                "versions": sorted(
                    versions, 
                    key=lambda v: (v["version_major"], v["version_minor"]),
                    reverse=True
                )
            })
    
    return conflicts
```

**Algorithm Analysis:**

**Time Complexity:**
- Query: O(n) where n = active documents
- Grouping: O(n) - single pass
- Sorting: O(k log k) where k = versions per group (usually k << 10)
- **Total: O(n)**

**Space Complexity:**
- Groups dict: O(n)
- Conflicts list: O(c) where c = number of conflicts
- **Total: O(n)**

**Why not use SQL GROUP BY?**

Could do:
```sql
SELECT 
  split_part(doc_id, '_v', 1) as base_id,
  COUNT(*) as count
FROM documents
WHERE is_active = true
GROUP BY base_id
HAVING COUNT(*) > 1
```

**Trade-offs:**
- ✅ SQL version: Faster (DB-level grouping)
- ❌ SQL version: Less flexible (hard to extract title pattern)
- ❌ SQL version: Needs RETURNING all fields → Complex query

**Current Python approach:**
- ✅ Flexible: Easy to customize grouping logic
- ✅ Readable: Clear algorithm
- ❌ Slower: Data transfer from DB

**Optimization for large datasets:**
```python
# Only fetch needed fields
docs = query.with_entities(
    Document.id,
    Document.doc_id,
    Document.title,
    Document.version_major,
    Document.version_minor,
    Document.doc_type
).all()
```

#### archive_version() - Implementation Details

```python
def archive_version(
    self,
    doc_id: str,
    superseded_by_doc_id: Optional[str] = None
) -> Document:
    # Step 1: Find document
    doc = self.db.query(Document).filter(Document.doc_id == doc_id).first()
    if not doc:
        raise ValueError(f"Document {doc_id} not found")
    
    # Step 2: Set archive flags
    doc.is_active = False
    doc.archived_at = datetime.utcnow()
    
    # Step 3: Set superseding relationship (if provided)
    if superseded_by_doc_id:
        superseding_doc = (
            self.db.query(Document)
            .filter(Document.doc_id == superseded_by_doc_id)
            .first()
        )
        if superseding_doc:
            doc.superseded_by_id = superseding_doc.id
    
    # Step 4: Commit
    self.db.commit()
    self.db.refresh(doc)
    
    return doc
```

**Why commit inside service method instead of letting caller commit?**

**Current approach (service commits):**
- ✅ **Atomicity**: One operation = one transaction
- ✅ **Simplicity**: Caller doesn't need to worry about commit
- ❌ **Flexibility**: Hard to bundle multiple operations

**Alternative (caller commits):**
```python
vs = VersioningService(db)
doc = vs.archive_version("v2023.0")  # No commit
# ... more operations ...
db.commit()  # Caller commits
```

- ✅ **Flexibility**: Can bundle operations
- ❌ **Error-prone**: Caller might forget to commit
- ❌ **Leaky abstraction**: Service internals exposed

**Best practice for this project:** Service commits, but provide batch operations:
```python
def archive_multiple(self, doc_ids: list[str]) -> list[Document]:
    """Archive multiple documents in single transaction."""
    archived = []
    for doc_id in doc_ids:
        doc = self._archive_version_no_commit(doc_id)  # Internal method
        archived.append(doc)
    
    self.db.commit()  # Single commit for all
    return archived
```

#### resolve_conflicts_auto() - Strategy Pattern

```python
def resolve_conflicts_auto(
    self,
    doc_type: Optional[str] = None,
    strategy: str = "keep_latest"
) -> list[dict]:
    conflicts = self.detect_conflicts(doc_type=doc_type)
    archived = []
    
    for conflict in conflicts:
        versions = conflict["versions"]
        
        # Strategy selection
        if strategy == "keep_latest":
            to_keep = versions[0]  # Already sorted by version desc
            to_archive = versions[1:]
        
        elif strategy == "keep_effective":
            versions_sorted = sorted(
                versions,
                key=lambda v: v["effective_date"] or date(1900, 1, 1),
                reverse=True
            )
            to_keep = versions_sorted[0]
            to_archive = [v for v in versions if v["doc_id"] != to_keep["doc_id"]]
        
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        # Execute archiving
        for ver in to_archive:
            doc = self.archive_version(
                ver["doc_id"],
                superseded_by_doc_id=to_keep["doc_id"]
            )
            archived.append({
                "doc_id": doc.doc_id,
                "title": doc.title,
                "version": f"{doc.version_major}.{doc.version_minor}",
                "superseded_by": to_keep["doc_id"]
            })
    
    return archived
```

**Design Pattern: Strategy**

Could refactor to use Strategy pattern:
```python
class ResolutionStrategy(ABC):
    @abstractmethod
    def select_version_to_keep(self, versions: list[dict]) -> dict:
        pass

class KeepLatestStrategy(ResolutionStrategy):
    def select_version_to_keep(self, versions: list[dict]) -> dict:
        return max(versions, key=lambda v: (v["version_major"], v["version_minor"]))

class KeepEffectiveStrategy(ResolutionStrategy):
    def select_version_to_keep(self, versions: list[dict]) -> dict:
        return max(versions, key=lambda v: v["effective_date"] or date.min)

# Usage
def resolve_conflicts_auto(self, strategy: ResolutionStrategy):
    for conflict in conflicts:
        to_keep = strategy.select_version_to_keep(conflict["versions"])
        ...
```

**Why not use Strategy pattern here?**

Current approach (string parameter):
- ✅ **Simple**: Easy to use from API (just pass string)
- ✅ **Serializable**: Can store strategy in config/DB
- ❌ **Not extensible**: Adding new strategy requires code change

Strategy pattern:
- ✅ **Extensible**: Easy to add new strategies
- ❌ **Complex**: Need to pass strategy object from API
- ❌ **Not serializable**: Can't store in DB easily

**For this use case:** String parameter is sufficient. If we need 10+ strategies, refactor to Strategy pattern.

---

### 3. API Layer (`app/main.py`)

#### Version Control Endpoints

**Endpoint: GET /api/versions/conflicts**

```python
@app.get("/api/versions/conflicts", response_model=list[VersionConflictDetail])
def detect_version_conflicts(
    doc_type: str | None = Query(None, description="Filter by document type")
):
    db = SessionLocal()
    vs = VersioningService(db)
    conflicts = vs.detect_conflicts(doc_type=doc_type)
    
    return [
        VersionConflictDetail(**c)
        for c in conflicts
    ]
```

**Why create new SessionLocal() per request instead of dependency injection?**

**Current approach:**
```python
db = SessionLocal()
vs = VersioningService(db)
```

**Better approach with FastAPI dependency:**
```python
from fastapi import Depends

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/api/versions/conflicts")
def detect_version_conflicts(
    doc_type: str | None = Query(None),
    db: Session = Depends(get_db)  # Injected
):
    vs = VersioningService(db)
    conflicts = vs.detect_conflicts(doc_type=doc_type)
    return [VersionConflictDetail(**c) for c in conflicts]
```

**Benefits of dependency injection:**
- ✅ **Auto cleanup**: `finally` ensures db.close()
- ✅ **Testability**: Easy to mock database
- ✅ **Consistency**: All endpoints use same pattern

**TODO: Refactor to use Depends(get_db)**

#### Integration with Chat Endpoint

```python
@app.post("/chat", response_model=ChatAnswer)
def chat(payload: ChatIn):
    db = SessionLocal()
    
    # Check for version conflicts
    version_warning = None
    if not payload.active_only:
        vs = VersioningService(db)
        conflicts = vs.detect_conflicts(
            doc_type=payload.doc_type,
            effective_on=payload.effective_on
        )
        if conflicts:
            version_warning = (
                f"⚠️ Phát hiện {len(conflicts)} xung đột phiên bản. "
                f"Kết quả có thể chứa nhiều phiên bản khác nhau của cùng một luật."
            )
    
    # ... retrieval and answer generation ...
    
    if version_warning:
        result.version_warning = version_warning
    
    return result
```

**Why check conflicts in chat endpoint?**

**Design rationale:**
- When user searches with `active_only=false`, they might retrieval conflicting versions
- Warning helps user understand answer might be ambiguous
- Encourages admin to resolve conflicts

**Performance concern:**
- `detect_conflicts()` runs on every chat request with `active_only=false`
- If many conflicts, this adds latency

**Optimization:**
- Cache conflict detection results (TTL 5 minutes)
- Only check if active_only=false (skip for default queries)

**Caching implementation:**
```python
from functools import lru_cache
from datetime import datetime, timedelta

_conflict_cache = {"data": [], "timestamp": None}

def get_conflicts_cached(doc_type=None):
    global _conflict_cache
    
    # Cache for 5 minutes
    if _conflict_cache["timestamp"] and \
       datetime.now() - _conflict_cache["timestamp"] < timedelta(minutes=5):
        return _conflict_cache["data"]
    
    # Refresh cache
    vs = VersioningService(SessionLocal())
    conflicts = vs.detect_conflicts(doc_type=doc_type)
    _conflict_cache = {
        "data": conflicts,
        "timestamp": datetime.now()
    }
    return conflicts
```

---

### 4. Migration (`alembic/versions/0002_add_versioning.py`)

```python
def upgrade() -> None:
    # Add columns
    op.add_column("documents", sa.Column("version_major", sa.Integer(), 
        nullable=False, server_default="1"))
    op.add_column("documents", sa.Column("version_minor", sa.Integer(), 
        nullable=False, server_default="0"))
    op.add_column("documents", sa.Column("is_active", sa.Boolean(), 
        nullable=False, server_default="true"))
    op.add_column("documents", sa.Column("effective_date", sa.Date(), 
        nullable=True))
    op.add_column("documents", sa.Column("archived_at", sa.DateTime(), 
        nullable=True))
    op.add_column("documents", sa.Column("superseded_by_id", sa.Integer(), 
        nullable=True))
    
    # Add foreign key
    op.create_foreign_key(
        "fk_documents_superseded_by_id",
        "documents", "documents",
        ["superseded_by_id"], ["id"],
        ondelete="SET NULL"
    )
    
    # Add indexes
    op.create_index("ix_documents_version_major", "documents", ["version_major"])
    op.create_index("ix_documents_version_minor", "documents", ["version_minor"])
    op.create_index("ix_documents_is_active", "documents", ["is_active"])
```

**Why server_default instead of just default?**

- `default=1` → Python-level default (application layer)
- `server_default="1"` → Database-level default (SQL DEFAULT)

**Benefits of server_default:**
- ✅ Works even if INSERT bypasses SQLAlchemy
- ✅ Visible in DB schema (SHOW CREATE TABLE)
- ✅ Migration works for existing rows (fills NULL with default)

**Why ondelete="SET NULL" for FK?**

```sql
FOREIGN KEY (superseded_by_id) REFERENCES documents(id) ON DELETE SET NULL
```

**Scenario:**
```
v2023 → superseded_by_id = 123 (v2024)
Admin deletes v2024 by mistake
```

**With SET NULL:**
- v2023.superseded_by_id becomes NULL
- v2023 still exists (data preserved)

**Without SET NULL (default CASCADE):**
- Deleting v2024 would CASCADE delete v2023!
- Data loss

**Alternative: ON DELETE RESTRICT:**
- Cannot delete v2024 if v2023 references it
- Forces admin to update v2023 first
- More safe but less flexible

**Trade-off:** SET NULL is reasonable for versioning (allow deleting superseding doc, relationship becomes unknown).

---

## Testing Strategy

### Unit Tests

**Test conflict detection:**
```python
def test_detect_conflicts_single_version(db):
    """No conflict with single active version."""
    doc = Document(doc_id="law_v1", version_major=1, is_active=True)
    db.add(doc)
    db.commit()
    
    vs = VersioningService(db)
    conflicts = vs.detect_conflicts()
    
    assert len(conflicts) == 0

def test_detect_conflicts_multiple_active(db):
    """Conflict with multiple active versions."""
    doc1 = Document(doc_id="law_v1", title="LAW (2023)", version_major=2023, is_active=True)
    doc2 = Document(doc_id="law_v2", title="LAW (2024)", version_major=2024, is_active=True)
    db.add_all([doc1, doc2])
    db.commit()
    
    vs = VersioningService(db)
    conflicts = vs.detect_conflicts()
    
    assert len(conflicts) == 1
    assert conflicts[0]["conflict_count"] == 2

def test_archive_version(db):
    """Archive sets flags correctly."""
    doc = Document(doc_id="law_v1", is_active=True)
    db.add(doc)
    db.commit()
    
    vs = VersioningService(db)
    archived = vs.archive_version("law_v1")
    
    assert archived.is_active == False
    assert archived.archived_at is not None
```

### Integration Tests

**Test chat with version warning:**
```python
def test_chat_warns_on_conflict(client, db):
    """Chat returns warning when conflicts detected."""
    # Setup: 2 active versions
    doc1 = create_document(db, "law_v2023", is_active=True)
    doc2 = create_document(db, "law_v2024", is_active=True)
    add_chunks(db, doc1, "Việt vị...")
    add_chunks(db, doc2, "KHÔNG việt vị...")
    
    # Chat with active_only=false
    response = client.post("/chat", json={
        "message": "Việt vị?",
        "active_only": False
    })
    
    data = response.json()
    assert "version_warning" in data
    assert "xung đột" in data["version_warning"]
```

### Performance Tests

**Benchmark conflict detection:**
```python
import time

def benchmark_conflict_detection(n_documents=10000):
    """Measure performance with large dataset."""
    db = SessionLocal()
    
    # Create n documents with some conflicts
    for i in range(n_documents):
        base = i // 5  # Groups of 5 → conflicts
        doc = Document(
            doc_id=f"law_{base}_v{i%5}",
            title=f"LAW {base}",
            version_major=2020 + (i % 5),
            is_active=True
        )
        db.add(doc)
    db.commit()
    
    # Benchmark
    vs = VersioningService(db)
    start = time.time()
    conflicts = vs.detect_conflicts()
    elapsed = time.time() - start
    
    print(f"Detected {len(conflicts)} conflicts from {n_documents} docs in {elapsed:.3f}s")
    assert elapsed < 1.0  # Should complete in <1 second
```

---

## Future Improvements

### 1. Soft Delete for Chunks

**Current:** Khi archive document, chunks vẫn tồn tại trong DB và được scan trong vector search.

**Improvement:** Add `is_archived` field to chunks:
```python
class Chunk(Base):
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

# When archiving document
def archive_version(self, doc_id: str):
    doc = ...
    doc.is_active = False
    
    # Also archive chunks
    for chunk in doc.chunks:
        chunk.is_archived = True
```

Vector search:
```sql
SELECT ... FROM chunks WHERE is_archived = false
ORDER BY embedding <=> :qvec
```

**Benefit:** Skip archived chunks → Faster search.

### 2. Version Diff API

**Feature:** Show what changed between versions.

```python
@app.get("/api/versions/diff/{doc_id_1}/{doc_id_2}")
def version_diff(doc_id_1: str, doc_id_2: str):
    """Compare two versions and show differences."""
    # Retrieve chunks from both versions
    chunks1 = get_chunks_for_doc(doc_id_1)
    chunks2 = get_chunks_for_doc(doc_id_2)
    
    # Use difflib to compute diff
    import difflib
    diff = difflib.unified_diff(
        [c.text for c in chunks1],
        [c.text for c in chunks2],
        lineterm=''
    )
    
    return {"diff": list(diff)}
```

### 3. Scheduled Archiving

**Feature:** Auto-archive based on effective_date.

```python
# Celery task or cron job
def auto_archive_expired_versions():
    """Archive versions that are no longer effective."""
    db = SessionLocal()
    today = date.today()
    
    # Find active docs with effective_date in past AND superseding version exists
    expired = db.query(Document).filter(
        Document.is_active == True,
        Document.effective_date < today,
        Document.superseded_by_id.isnot(None)
    ).all()
    
    vs = VersioningService(db)
    for doc in expired:
        vs.archive_version(doc.doc_id)
        print(f"Auto-archived {doc.doc_id}")
```

### 4. Version Comparison in Chat

**Feature:** User can ask to compare versions.

```bash
User: "So sánh luật việt vị giữa 2023 và 2024"
```

```python
# Detect intent
if "so sánh" in message and "2023" in message and "2024" in message:
    # Retrieve from both versions
    chunks_2023 = retrieve(db, "việt vị", effective_on=date(2023, 6, 1))
    chunks_2024 = retrieve(db, "việt vị", effective_on=date(2024, 6, 1))
    
    # Generate comparison answer
    answer = llm.generate(f"""
    So sánh luật việt vị giữa 2 phiên bản:
    
    2023: {chunks_2023[0]['text']}
    2024: {chunks_2024[0]['text']}
    
    Chỉ ra sự khác biệt chính.
    """)
```

---

## Common Pitfalls

### Pitfall 1: Forgetting to archive old version

**Wrong:**
```bash
# Ingest new version
python ingest.py data/law_2024/ --doc-id law_v2024

# Forget to archive v2023 → CONFLICT!
```

**Correct:**
```bash
# Ingest + archive in one step
python ingest.py data/law_2024/ --doc-id law_v2024 --archive-old law_v2023
```

Or use script:
```python
def ingest_and_archive(new_pdf, old_doc_id):
    # Ingest new
    ingest_pdf(new_pdf)
    
    # Archive old
    vs = VersioningService(SessionLocal())
    vs.archive_version(old_doc_id, superseded_by_doc_id=new_doc_id)
```

### Pitfall 2: Circular superseding

**Wrong:**
```python
vs.archive_version("v2023", superseded_by_doc_id="v2024")
vs.archive_version("v2024", superseded_by_doc_id="v2023")  # Circular!
```

**Prevention:** Add validation in `archive_version()`:
```python
if superseded_by_doc_id:
    # Check for circular reference
    if self._forms_circular_chain(doc.id, superseding_doc.id):
        raise ValueError("Circular superseding chain detected!")
```

### Pitfall 3: Not setting effective_date

**Problem:** All docs have `effective_date=None` → Historical queries don't work.

**Solution:** Always set effective_date when ingesting:
```python
doc = Document(
    doc_id="law_v2024",
    effective_date=date(2024, 1, 1)  # Always set!
)
```

---

## Debugging Tips

### Debug conflict detection

```python
# In Python shell
from app.rag.versioning import VersioningService
from app.db import SessionLocal

db = SessionLocal()
vs = VersioningService(db)

# See all active docs
active = db.query(Document).filter(Document.is_active == True).all()
for d in active:
    print(f"{d.doc_id}: v{d.version_major}.{d.version_minor}, title={d.title}")

# See grouping
conflicts = vs.detect_conflicts()
for c in conflicts:
    print(f"\nConflict in {c['base_doc']}:")
    for v in c['versions']:
        print(f"  - {v['doc_id']}: v{v['version']}")
```

### Debug version chains

```python
def print_version_chain(doc_id):
    """Print full superseding chain."""
    db = SessionLocal()
    doc = db.query(Document).filter_by(doc_id=doc_id).first()
    
    print(f"Version chain for {doc_id}:")
    current = doc
    visited = set()
    
    while current:
        print(f"  → {current.doc_id} (v{current.version_major}.{current.version_minor})")
        
        if current.id in visited:
            print("  ⚠️ CIRCULAR CHAIN DETECTED!")
            break
        visited.add(current.id)
        
        # Follow superseded_by link
        if current.superseded_by_id:
            current = db.query(Document).get(current.superseded_by_id)
        else:
            print("  → (end)")
            break
```

### Debug effective_date queries

```sql
-- Documents effective on 2023-06-01
SELECT doc_id, version_major, version_minor, effective_date
FROM documents
WHERE is_active = true
  AND (effective_date IS NULL OR effective_date <= '2023-06-01')
ORDER BY version_major DESC, version_minor DESC;
```

---

## References

- [VERSION_CONTROL.md](VERSION_CONTROL.md) - User-facing documentation
- [SQLAlchemy Self-Referential Relationships](https://docs.sqlalchemy.org/en/20/orm/self_referential.html)
- [Alembic Migration Cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html)
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)

---

**Last Updated:** 2026-03-03  
**Version:** 1.0  
**Maintainer:** Development Team
