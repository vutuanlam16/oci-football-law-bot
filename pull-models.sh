#!/bin/bash
set -e

echo "📥 Pulling Ollama models..."

# Pull chat model
echo ""
echo "1. Pulling chat model: qwen2.5:3b-instruct (~2GB)..."
docker compose exec ollama ollama pull qwen2.5:3b-instruct

# Pull embedding model
echo ""
echo "2. Pulling embedding model: nomic-embed-text (~274MB)..."
docker compose exec ollama ollama pull nomic-embed-text

# List models
echo ""
echo "✅ Installed models:"
docker compose exec ollama ollama list

echo ""
echo "🎉 Models ready! You can now use the chat API."
