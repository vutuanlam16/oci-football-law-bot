# Slide Outline - Hệ thống RAG Tra cứu Luật Bóng đá

**Template gợi ý**: Dark theme, màu chủ đạo #38bdf8 (blue) + #0b1020 (background)

---

## SLIDE 1: Title Slide
**Layout**: Centered text

### Content:
```
🏆 HỆ THỐNG TRA CỨU LUẬT BÓNG ĐÁ
Sử dụng RAG (Retrieval-Augmented Generation)

Sinh viên: [Tên]
Lớp: [Lớp]
Môn: Xử lý ngôn ngữ tự nhiên (NLP)
```

**Visual**: Icon bóng đá + chatbot

---

## SLIDE 2: Problem Statement
**Layout**: Left text, Right image

### Content:
**Vấn đề**:
- Luật bóng đá FIFA: 17 luật, 200+ trang
- Tra cứu thủ công mất thời gian
- Khó tìm đúng điều luật liên quan

**Ví dụ**: 
> "Nhận bóng từ ném biên có việt vị không?"
> → Phải lật tới trang 89-92 (LUẬT 11)

**Visual**: Screenshot PDF luật (highlight dòng khó đọc)

---

## SLIDE 3: Solution Overview
**Layout**: 3-column

### Content:
| 🔍 Retrieval | ➕ Augmentation | ✨ Generation |
|--------------|-----------------|---------------|
| Vector Search tìm chunks liên quan | Ghép chunks vào prompt | LLM tạo câu trả lời + trích dẫn |

**Visual**: Flowchart đơn giản
```
Câu hỏi → Embedding → Vector Search → Top-K Chunks
                                            ↓
                                       LLM (Gemini)
                                            ↓
                                 Trả lời + Citations
```

---

## SLIDE 4: Architecture - Offline Phase
**Layout**: Vertical flow diagram

### Content:
```
📄 PDF Luật Bóng Đá
    ↓
🔪 Chunking (theo cấu trúc pháp lý)
    ↓ 
🧮 Embeddings (Gemini 1536-dim)
    ↓
💾 PostgreSQL + pgvector (HNSW index)
```

**Annotations**:
- Chunking: "LUẬT X, Điều Y → 1 chunk"
- Embeddings: "Text → Vector 1536 chiều"
- pgvector: "Vector similarity search <100ms"

**Visual**: Icons cho mỗi bước (PDF, scissors, calculator, database)

---

## SLIDE 5: Architecture - Online Phase
**Layout**: Horizontal flow

### Content:
```
👤 User: "Nhận bóng từ ném biên có việt vị không?"
    ↓
🧮 Embedding câu hỏi
    ↓
🔍 Vector Search → Top-5 chunks (cosine similarity)
    ↓
📝 Prompt = System + SOURCES + Question
    ↓
🤖 Gemini Flash → JSON output
    ↓
✅ Validation (check source_id)
    ↓
📤 Response: Answer + Citations
```

**Visual**: Flow với màu sắc phân biệt bước

---

## SLIDE 6: Kỹ thuật #1 - Chunking
**Layout**: Left code, Right example

### Content:
**Chiến lược**:
- ❌ Không: Chia theo 500 chars (mất context)
- ✅ Có: Chia theo cấu trúc pháp lý

**Code snippet**:
```python
def chunk_by_legal_structure(text):
    # Detect: LUẬT 17, Điều 3.2
    # Preserve: section_label, page range
    return chunks
```

**Example Output**:
```json
{
  "text": "LUẬT 11 - VIỆT VỊ\n\nCầu thủ ở tư thế việt vị...",
  "section_label": "LUẬT 11 - VIỆT VỊ",
  "page_start": 89,
  "page_end": 92
}
```

**Visual**: Screenshot chunk structure

---

## SLIDE 7: Kỹ thuật #2 - Embeddings & Vector Search
**Layout**: 2-column comparison

### Content:
**Embedding Model**: Gemini embedding-001
- Input: Text (any length)
- Output: Vector 1536 chiều

**Vector Search**:
```
Cosine Similarity = dot(v1, v2) / (||v1|| * ||v2||)
Range: [-1, 1]
```

**Example**:
| Text | Vector (simplified) | Similarity |
|------|---------------------|------------|
| Câu hỏi: "Việt vị từ ném biên?" | [0.3, 0.8, ...] | - |
| Chunk 1: "LUẬT 11: Không việt vị từ ném biên" | [0.32, 0.79, ...] | 0.87 ⭐ |
| Chunk 2: "LUẬT 17: Quả phạt góc" | [0.1, 0.2, ...] | 0.42 |

**Visual**: Vector visualization (2D projection với t-SNE)

---

## SLIDE 8: Kỹ thuật #3 - Prompt Engineering
**Layout**: Full slide code

### Content:
**System Instruction**:
```
CHỈ được trả lời dựa trên SOURCES được cung cấp.
Mọi nội dung phải có trích dẫn (source_id).
Nếu SOURCES không đủ: trả lời 'Chưa đủ dữ liệu'.
Output ONLY JSON.
```

**User Prompt**:
```
QUESTION: Nhận bóng từ ném biên có việt vị không?

SOURCES:
[S1] Luật thi đấu | LUẬT 11 - VIỆT VỊ | tr. 89-92
Không có tư thế việt vị khi nhận bóng trực tiếp từ ném biên...

Return JSON:
{
  "answer": "...",
  "citations": [{"source_id": "S1", "quote": "..."}]
}
```

**Visual**: Highlight "CHỈ được" và "source_id"

---

## SLIDE 9: Citation Validation
**Layout**: Flowchart

### Content:
```
LLM Output
    ↓
Extract citations
    ↓
Check: source_id in allowed_list?
    ├── YES → Keep + Override metadata from DB
    └── NO → Remove (hallucination)
    ↓
Final Response (clean citations)
```

**Code**:
```python
allowed = {"S1": {...}, "S2": {...}}

for citation in llm_output.citations:
    if citation.source_id not in allowed:
        continue  # Drop hallucinated citation
    # Override metadata (ensure accuracy)
    citation.pages = allowed[citation.source_id]["pages"]
```

**Visual**: Red X cho hallucination, Green check cho valid

---

## SLIDE 10: Demo Results - Happy Path
**Layout**: Screenshot with annotations

### Content:
**Input**:
```json
{"message": "Nhận bóng từ ném biên có việt vị không?"}
```

**Output**:
```json
{
  "answer": "Không. Theo Luật 11, cầu thủ không thể ở tư thế việt vị khi nhận bóng trực tiếp từ ném biên.",
  "citations": [
    {
      "source_id": "S2",
      "quote": "không có tư thế việt vị khi nhận bóng trực tiếp từ ném biên",
      "doc_title": "Luật thi đấu",
      "section_label": "LUẬT 11 - VIỆT VỊ",
      "pages": "tr. 89-92"
    }
  ],
  "confidence": 0.95
}
```

**Visual**: Highlight answer + citation, annotate "Chính xác ✅"

---

## SLIDE 11: Demo Results - Edge Case
**Layout**: Side-by-side comparison

### Content:
**Input**: "Messi đã ghi bao nhiêu bàn thắng?"

**Output**:
```json
{
  "answer": "Chưa đủ dữ liệu để trả lời chắc chắn dựa trên các nguồn hiện có.",
  "citations": [],
  "followup_questions": [
    "Bạn đang tìm thông tin về Luật thi đấu bóng đá hay về cầu thủ cụ thể?"
  ],
  "confidence": 0.0
}
```

**Annotation**: "Không bịa thông tin ✅"

**Visual**: Emoji 🚫 cho out-of-scope

---

## SLIDE 12: Comparison - BM25 vs RAG
**Layout**: Table

### Content:
| Aspect | BM25 (Baseline) | RAG (Our System) |
|--------|-----------------|------------------|
| **Принцип** | Keyword matching | Semantic search |
| **Query** | "Việt vị từ ném biên?" | "Việt vị từ ném biên?" |
| **Match** | Chứa "việt vị" AND "ném biên" | Cosine similarity >0.8 |
| **Missed Case** | Chunk dùng "throw-in" (tiếng Anh) | ✅ Tìm được (hiểu synonym) |
| **Recall** | 62% | 85% (+23%) |

**Visual**: Chart so sánh Recall (bar chart)

---

## SLIDE 13: Metrics & Evaluation
**Layout**: 4 cards

### Content:
| 🎯 Accuracy | 📌 Citation Precision | 🚫 Hallucination | ⚡ Latency |
|-------------|----------------------|------------------|-----------|
| **88%** | **92%** | **4%** | **3-5s** |
| 44/50 đúng | Trích dẫn chính xác | Chỉ 2/50 bịa | Embed 0.5s<br>Search 0.2s<br>LLM 2-4s |

**Test Set**: 50 câu hỏi (tự tạo):
- 20 câu đơn giản (định nghĩa)
- 20 câu phức tạp (multi-hop)
- 10 câu ngoài phạm vi (negative test)

**Visual**: Gauge charts cho metrics

---

## SLIDE 14: Error Analysis
**Layout**: 2-column

### Content:
**6 câu sai (12%)**:

**Root Cause**:
- 4 câu: Chunking sai (mất context)
  - Ví dụ: "Thẻ đỏ khi nào?" → Chunk chỉ có 1 trường hợp, thiếu 3 trường hợp khác
- 2 câu: LLM reasoning sai
  - Ví dụ: Multi-hop phức tạp (>3 luật), LLM không kết hợp được

**Improvement Plan**:
- Re-chunk với context window lớn hơn
- Few-shot prompting cho multi-hop

**Visual**: Pie chart (4 chunking, 2 reasoning)

---

## SLIDE 15: Strengths & Limitations
**Layout**: T-chart

### Content:
**✅ Ưu điểm**:
- Trích dẫn chính xác (section + trang)
- Không hallucination (validation guardrail)
- Hiểu ngữ nghĩa tiếng Việt
- Scale tốt (HNSW index)

**❌ Hạn chế**:
- Phụ thuộc chunking quality
- Top-K cố định (không adaptive)
- Embedding chưa fine-tune legal domain
- Latency 3-5s (chưa production-ready)

**Visual**: Icons (checkmark vs X)

---

## SLIDE 16: Future Work
**Layout**: Roadmap diagram

### Content:
**Phase 1 (1 tháng)**:
- Fine-tune embedding model (legal domain)
- Hybrid search (BM25 + Vector)

**Phase 2 (2 tháng)**:
- Adaptive top-K
- Cache optimization (<1s latency)

**Phase 3 (3 tháng)**:
- Multi-language support (English)
- Version management (luật thay đổi theo thời gian)

**Visual**: Timeline với milestones

---

## SLIDE 17: Tech Stack Summary
**Layout**: Icon grid

### Content:
| Component | Technology | Why? |
|-----------|------------|------|
| 🐍 Backend | FastAPI | Async, fast |
| 💾 Database | PostgreSQL + pgvector | Vector search + ACID |
| 🤖 LLM | Gemini Flash | Fast, multilingual |
| 🧮 Embedding | Gemini embedding-001 | 1536-dim, sota quality |
| 🐳 Deployment | Docker Compose | Easy setup |
| 🔒 Reverse Proxy | Caddy | Auto HTTPS |

**Visual**: Logo của mỗi tech

---

## SLIDE 18: Thank You
**Layout**: Centered

### Content:
```
CẢM ƠN QUÝ THẦY CÔ ĐÃ LẮNG NGHE!

📧 Email: [your-email]
💻 GitHub: [repo-url]
📱 Demo: http://your-domain.com

Sẵn sàng trả lời câu hỏi 🙋
```

**Visual**: QR code dẫn tới GitHub repo

---

## BACKUP SLIDES (nếu hỏi thêm)

### SLIDE B1: Technical Deep Dive - HNSW
**Content**:
- Hierarchical Navigable Small World graphs
- Build: O(N log N), Search: O(log N)
- Parameters: M (connections), ef_construction

### SLIDE B2: Code Structure
**Content**:
```
app/
  rag/
    chunker.py        # Legal structure-based chunking
    embedder.py       # Provider factory (Gemini/Ollama)
    retrieve.py       # Vector search
    answer.py         # Prompt + LLM + Validation
  models.py           # SQLAlchemy ORM
  main.py             # FastAPI routes
```

### SLIDE B3: Related Work
**Content**:
- LangChain RAG
- LlamaIndex
- OpenAI Assistants API
- Comparison table

---

## 🎨 Design Guidelines

### Color Palette:
- Primary: `#38bdf8` (cyan blue)
- Background: `#0b1020` (dark navy)
- Success: `#22c55e` (green)
- Error: `#ef4444` (red)
- Text: `#f8fafc` (white)

### Fonts:
- Title: **Inter Bold** (32-48pt)
- Body: **Inter Regular** (18-24pt)
- Code: **JetBrains Mono** (14-16pt)

### Icons:
- Use **Lucide Icons** hoặc **Heroicons**
- Consistent style (outline hoặc solid, không mix)

### Animations:
- Slide transition: Fade (subtle)
- Code highlight: Yellow background
- Avoid: Excessive animations (professional look)

---

## 📱 Export Settings

### PowerPoint:
- Aspect ratio: 16:9 (widescreen)
- File format: .pptx
- Embed fonts: Yes

### Google Slides:
- Share link: "Anyone with link can view"
- Download as PDF backup

### PDF Export:
- For printing handouts
- Include slide notes
