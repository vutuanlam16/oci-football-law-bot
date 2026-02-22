# 🚀 Hướng dẫn chạy local (1 file)

## 1) Chuẩn bị
- Docker Desktop đã chạy
- File `.env` đã có `POSTGRES_PASSWORD` (nếu chưa thì sửa trước)

## 2) Khởi động dịch vụ

```bash
docker compose down
docker compose up -d --force-recreate
docker compose ps
```

Kỳ vọng port mapping:
- `0.0.0.0:8000->8000/tcp` (app)
- `0.0.0.0:5432->5432/tcp` (db)
- `0.0.0.0:11434->11434/tcp` (ollama)

## 3) Pull models Ollama (lần đầu)

```bash
docker compose exec ollama ollama pull qwen2.5:3b-instruct
docker compose exec ollama ollama pull nomic-embed-text
```

## 4) Test health

```bash
curl http://127.0.0.1:8000/healthz
```

Kết quả mong đợi:

```json
{"status":"ok"}
```

## 5) Ingest PDF

Copy file PDF vào `data/raw/` rồi chạy:

```bash
docker compose exec -w /app app python -m scripts.ingest_folder \
  --pdf-dir /data/raw \
  --doc-type laws
```

## 6) Test API

```bash
curl -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"Luật việt vị là gì?","top_k":5}'
```

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Nhận bóng từ ném biên có việt vị không?","top_k":8}'
```

## 7) Lệnh hữu ích

```bash
docker compose logs -f app
docker compose logs -f db
docker compose logs -f ollama
```

```bash
docker compose exec db psql -U postgres -d football_law
```

## 8) Troubleshooting nhanh

- `curl` không vào được 8000: kiểm tra `docker compose ps` và port mapping.
- Lỗi `EMBED_DIM mismatch`: chắc chắn `EMBED_DIM=768` và model `nomic-embed-text`.
- `No sources found`: chưa ingest PDF.
