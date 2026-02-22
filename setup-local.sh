#!/bin/bash
set -e

echo "🚀 Setting up local development environment..."

# 1. Khởi động Database
echo ""
echo "📦 Starting PostgreSQL database..."
docker compose up -d db
echo "⏳ Waiting for database to be healthy..."
sleep 10

# 2. Kiểm tra database
echo ""
echo "🔍 Checking database status..."
docker compose exec db psql -U postgres -d football_law -c "SELECT version();" || echo "Database not ready yet"

# 3. Khởi động Ollama
echo ""
echo "🤖 Starting Ollama service..."
docker compose up -d ollama
echo "⏳ Waiting for Ollama to start..."
sleep 15

# 4. Khởi động App (sẽ tự động chạy migrations)
echo ""
echo "🌐 Starting FastAPI application..."
docker compose up -d app

# 5. Đợi app khởi động
echo "⏳ Waiting for app to start..."
sleep 10

# 6. Kiểm tra status
echo ""
echo "✅ Services status:"
docker compose ps

echo ""
echo "📊 Next steps:"
echo "1. Pull Ollama models: ./pull-models.sh"
echo "2. Check logs: docker compose logs -f app"
echo "3. Test API: curl http://localhost:8000/healthz"
echo "4. Access docs: http://localhost:8000/docs"
