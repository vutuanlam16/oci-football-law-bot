# Chatbot Evaluation

Hệ thống đánh giá độ chính xác của RAG chatbot luật bóng đá.

## 📁 Files

- **test_dataset.json**: Bộ 20 câu hỏi test với expected answers
- **evaluate_chatbot.py**: Script đánh giá chatbot
- **run_evaluation.sh**: Bash script để chạy evaluation
- **evaluation_report_*.json**: Báo cáo kết quả đánh giá (auto-generated)

## 🚀 Cách sử dụng

### Bước 1: Chuẩn bị

Đảm bảo server đang chạy:

```bash
# Option 1: Docker
docker-compose up -d

# Option 2: Local
uvicorn app.main:app --reload
```

### Bước 2: Chạy evaluation

```bash
cd /Users/lamvu/Downloads/oci-football-law-bot

# Make script executable
chmod +x evaluation/run_evaluation.sh

# Run evaluation
./evaluation/run_evaluation.sh
```

### Bước 3: Xem kết quả

Kết quả sẽ được in ra console và lưu vào file JSON:

```
evaluation/evaluation_report_<timestamp>.json
```

## 📊 Evaluation Metrics

### 1. Answer Rate
- % câu hỏi chatbot trả lời được (không trả lời rỗng)

### 2. Source Rate  
- % câu trả lời có trích dẫn nguồn (citations)

### 3. Keyword Score
- % keywords mong đợi xuất hiện trong câu trả lời
- Weight: 40% trong overall accuracy

### 4. Semantic Similarity
- Độ tương đồng ngữ nghĩa giữa câu trả lời và expected answer
- Sử dụng Ollama embeddings (nomic-embed-text)
- Weight: 50% trong overall accuracy

### 5. Overall Accuracy
- Tổng hợp: `0.4 * keyword + 0.5 * semantic + 0.1 * (có nguồn trích dẫn)`

### 6. Response Time
- Thời gian trung bình để chatbot trả lời

## 📋 Test Dataset

Dataset gồm 20 câu hỏi chia thành các danh mục:

| Category | Questions |
|----------|-----------|
| offside | 4 |
| foul | 2 |
| penalty | 2 |
| ball_in_out | 2 |
| handball | 2 |
| substitution | 1 |
| time | 1 |
| goalkeeper | 1 |
| corner_kick | 1 |
| throw_in | 1 |
| goal_kick | 1 |
| free_kick | 1 |
| advantage | 1 |

**Total: 20 questions**

## 🔧 Tùy chỉnh Test Dataset

Chỉnh sửa `test_dataset.json`:

```json
{
  "id": 21,
  "category": "your_category",
  "question": "Câu hỏi của bạn?",
  "expected_answer": "Câu trả lời mong đợi",
  "keywords": ["keyword1", "keyword2", "keyword3"]
}
```

**Keywords**: Các từ khóa quan trọng cần xuất hiện trong câu trả lời.

## 📈 Đọc kết quả

### Console Output

```
📊 KẾT QUẢ ĐÁNH GIÁ CHATBOT
==================================================

📈 OVERALL METRICS:
  • Tổng câu hỏi: 20
  • Trả lời được: 20/20 (100.0%)
  • Có trích dẫn nguồn: 18/20 (90.0%)

🎯 ACCURACY SCORES:
  • Overall Accuracy: 87.5%
  • Keyword Match: 82.3%
  • Semantic Similarity: 91.2%
  • Keyword Coverage: 78.5%

⚡ PERFORMANCE:
  • Avg Response Time: 1.23s

📂 SCORES BY CATEGORY:
  • offside            : 92.1%
  • penalty            : 88.5%
  • foul               : 85.2%
  ...
```

### JSON Report

File `evaluation_report_*.json` chứa:

```json
{
  "timestamp": "2026-03-03T10:30:00",
  "total_questions": 20,
  "avg_accuracy_score": 0.875,
  "category_scores": {
    "offside": 0.921,
    "penalty": 0.885
  },
  "detailed_results": [
    {
      "test_id": 1,
      "question": "Thế nào là việt vị?",
      "actual_answer": "...",
      "accuracy_score": 0.95,
      "keyword_score": 0.90,
      "semantic_score": 0.98,
      ...
    }
  ]
}
```

## 🎯 Benchmark Targets

| Metric | Target | Good | Excellent |
|--------|--------|------|-----------|
| Overall Accuracy | >70% | >80% | >90% |
| Answer Rate | >90% | >95% | 100% |
| Source Rate | >70% | >85% | >95% |
| Response Time | <3s | <2s | <1s |
| Keyword Match | >60% | >75% | >85% |
| Semantic Similarity | >70% | >85% | >95% |

## 🐛 Troubleshooting

### Server không chạy

```bash
docker-compose up -d
# hoặc
uvicorn app.main:app --reload
```

### Ollama không chạy

Semantic similarity sẽ bị disable (score = 0). Để bật:

```bash
ollama serve
ollama pull nomic-embed-text
```

### Import numpy error

```bash
pip install numpy
```

## 📝 Notes

- **Keyword matching**: Case-insensitive, kiểm tra substring
- **Semantic similarity**: Cần Ollama + nomic-embed-text model
- **Timeout**: Mỗi request có timeout 30s
- **Rate limiting**: Sleep 0.5s giữa các requests để tránh overload

## 🔄 Continuous Evaluation

Để track accuracy theo thời gian:

```bash
# Chạy hàng ngày
crontab -e

# Add line:
0 9 * * * cd /path/to/project && ./evaluation/run_evaluation.sh >> evaluation/logs.txt 2>&1
```

## 📚 Related Documentation

- [Version Control Guide](../VERSION_CONTROL.md)
- [API Documentation](../README.md)
- [RAG System Overview](../app/rag/)
