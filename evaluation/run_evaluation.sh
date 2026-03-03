#!/bin/bash

# Script để chạy evaluation cho chatbot

set -e

echo "======================================"
echo "🧪 CHATBOT EVALUATION RUNNER"
echo "======================================"

# Check if server is running
echo ""
echo "🔍 Checking if API server is running..."
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ API server is not running on http://localhost:8000"
    echo "📝 Please start the server first:"
    echo "   docker-compose up -d"
    echo "   OR"
    echo "   uvicorn app.main:app --reload"
    exit 1
fi

echo "✅ API server is running"

# Check if Ollama is running
echo ""
echo "🔍 Checking if Ollama is running..."
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama is not running - semantic similarity will be disabled"
    echo "   Start Ollama for full evaluation: ollama serve"
else
    echo "✅ Ollama is running"
fi

# Install dependencies
echo ""
echo "📦 Installing evaluation dependencies..."
pip install -q numpy requests

# Run evaluation
echo ""
echo "🚀 Starting evaluation..."
echo ""

python evaluation/evaluate_chatbot.py

echo ""
echo "✅ Evaluation completed!"
echo "📊 Check evaluation/ folder for detailed reports"
