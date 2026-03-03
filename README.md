# OCI Always Free – Full Stack (FastAPI + Postgres/pgvector + Ollama + Caddy)

Gói này dựng một chatbot **tra cứu luật bóng đá** (RAG + citations) theo đúng tinh thần “**IE → retrieval → constrained generation → verification**” (bắt buộc trích dẫn, không có nguồn thì phải hỏi lại / từ chối) trong blueprint bạn đã mô tả. fileciteturn0file0

## 1) Kiến trúc

- **FastAPI**: API `/chat`, `/search` (RAG + citations)
- **Postgres + pgvector**: lưu chunks + embeddings + metadata trang/điều để trích dẫn
- **Ollama**:
  - Chat LLM: `POST /api/chat` citeturn3search0
  - Embeddings: `POST /api/embed` citeturn0search2
  - Health: `GET /api/version` citeturn2search1
- **Caddy reverse proxy**: HTTPS tự động khi có domain (ACME). citeturn1search0

Docker image `pgvector/pgvector:pg16-trixie` hỗ trợ cả `linux/amd64` và `linux/arm64` (hợp cho OCI Ampere). citeturn0search1

---

## 2) Yêu cầu trước khi chạy

1) **Một domain** trỏ A record tới public IP của VM (để Caddy cấp HTTPS tự động). citeturn1search0  
2) OCI Security List / NSG mở inbound:
   - TCP **22** (SSH)
   - TCP **80**, **443** (HTTP/HTTPS)
3) VM Ubuntu 22.04 / Oracle Linux (khuyến nghị Ubuntu để dễ thao tác)

---

## 3) Deploy trên OCI (Always Free)

### 3.1. SSH vào VM
```bash
ssh ubuntu@<PUBLIC_IP>
```

### 3.2. Cài Docker + docker compose plugin (Ubuntu)
```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

sudo usermod -aG docker $USER
newgrp docker
```

### 3.3. Clone repo
```bash
git clone <YOUR_REPO_URL>
cd oci-football-law-bot
cp .env.example .env
```

### 3.4. Sửa `.env`
Bắt buộc:
- `DOMAIN=...`
- `ACME_EMAIL=...`
- `POSTGRES_PASSWORD=...` (đổi mạnh)
- `CHAT_MODEL=...`
- `EMBED_MODEL=...` (khuyến nghị `nomic-embed-text` vì DB đang cố định vector 768 chiều)

### 3.5. Start services
```bash
docker compose up -d --build
docker compose ps
```

---

## 4) Pull model trong Ollama (lần đầu)

Container `ollama` không tự pull model.
Bạn pull thủ công:

```bash
docker compose exec ollama ollama pull qwen2.5:3b-instruct
docker compose exec ollama ollama pull nomic-embed-text
```

> Lưu ý: API chat dùng `POST /api/chat` và embedding dùng `POST /api/embed`. citeturn3search0turn0search2

---

## 5) Ingest PDF luật vào hệ thống

1) Copy PDFs vào server:
```bash
mkdir -p data/raw
# scp các file PDF vào data/raw/
```

2) Chạy ingest:
```bash
docker compose exec app python scripts/ingest_folder.py --pdf-dir /data/raw --doc-type laws
```

> Nếu ingest thành công, DB sẽ có `documents` và `chunks` (kèm embedding + page range).

---

## 6) Test API

### 6.1. /search (chỉ retrieval + citations)
```bash
curl -X POST https://$DOMAIN/search \
  -H "Content-Type: application/json" \
  -d '{"query":"Nhận bóng từ ném biên có việt vị không?","top_k":5}'
```

### 6.2. /chat (RAG + answer + citations)
```bash
curl -X POST https://$DOMAIN/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Nhận bóng từ ném biên có việt vị không?","top_k":8}'
```

---

## 7) Version Control & Conflict Detection

Hệ thống hỗ trợ **quản lý nhiều phiên bản** của cùng một luật (ví dụ: Luật Bóng đá 2023, 2024, 2025) với tính năng:

- ✅ **Version tracking** (major.minor versioning)
- ✅ **Conflict detection** (phát hiện nhiều phiên bản active)
- ✅ **Historical queries** (tra cứu luật theo thời điểm)
- ✅ **Auto-archive** versions cũ

### 7.1. Migrate database để thêm version fields

```bash
docker compose exec app alembic upgrade head
```

### 7.2. Kiểm tra conflicts

```bash
curl http://localhost:8000/api/versions/conflicts
```

### 7.3. Xem thống kê versions

```bash
curl http://localhost:8000/api/versions/stats
```

### 7.4. Chat với version control

```bash
# Chỉ tìm trong versions active (mặc định)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Thế nào là việt vị?","active_only":true}'

# Tìm luật tại thời điểm cụ thể (historical query)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Luật việt vị năm 2023?","active_only":false,"effective_on":"2023-06-01"}'
```

📖 **Xem chi tiết**: [VERSION_CONTROL.md](VERSION_CONTROL.md)

---

## 8) Notes vận hành (khuyến nghị)

- Không expose Postgres/ollama ra internet.
- Nếu muốn khóa truy cập API (demo public), thêm Basic Auth trong Caddyfile.
- Khi update PDF (phiên bản luật mới), sử dụng version control để quản lý (xem [VERSION_CONTROL.md](VERSION_CONTROL.md)).

---

## 9) Files quan trọng

- `docker-compose.yml` – toàn bộ stack
- `ops/caddy/Caddyfile` – reverse proxy + HTTPS
- `alembic/versions/` – database migrations
  - `0001_init.py` – initial schema + vector index
  - `0002_add_versioning.py` – version control fields
- `scripts/ingest_folder.py` – ingest PDFs
- `app/rag/versioning.py` – version management service
- `app/rag/*` – retrieval + embedding + generation (Ollama/Gemini)

**Documentation:**
- [VERSIONING_QUICK_START.md](VERSIONING_QUICK_START.md) – Bắt đầu nhanh với version control (5 phút)
- [VERSION_CONTROL.md](VERSION_CONTROL.md) – Hướng dẫn chi tiết version control (user-facing)
- [VERSIONING_INTERNALS.md](VERSIONING_INTERNALS.md) – Implementation details cho developers
- [VERSIONING_SLIDES_4.md](VERSIONING_SLIDES_4.md) – Slides trình bày 4 slides (3 phút)
- [DEMO.md](DEMO.md) – Kịch bản demo cho NLP course
- [PRESENTATION_SCRIPT.md](PRESENTATION_SCRIPT.md) – Script trình bày chi tiết

