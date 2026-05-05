#!/usr/bin/env bash
# ============================================================
# pull_model.sh — Tải model Ollama cho AI Service
# Chạy 1 lần sau khi cài Ollama
# Usage: bash scripts/pull_model.sh [model_name]
# ============================================================

set -euo pipefail

MODEL_NAME="${1:-qwen2.5:7b}"

echo "╔══════════════════════════════════════════╗"
echo "║  SCI-Translate — Ollama Model Setup      ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Kiểm tra Ollama đã cài chưa
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama chưa được cài đặt!"
    echo "   Hướng dẫn cài đặt:"
    echo "   - Linux/WSL: curl -fsSL https://ollama.ai/install.sh | sh"
    echo "   - macOS:     brew install ollama"
    echo "   - Windows:   https://ollama.com/download/windows"
    exit 1
fi

echo "✅ Ollama version: $(ollama --version)"
echo ""

# Kiểm tra Ollama daemon
if ! ollama list &> /dev/null 2>&1; then
    echo "⚠️  Ollama daemon chưa chạy. Đang khởi động..."
    ollama serve &
    sleep 3
fi

# Pull model
echo "📥 Đang tải model: ${MODEL_NAME}..."
echo "   (Lần đầu có thể mất vài phút tùy dung lượng model)"
echo ""
ollama pull "${MODEL_NAME}"

echo ""
echo "✅ Model '${MODEL_NAME}' đã sẵn sàng!"
echo ""

# Liệt kê models đã cài
echo "📋 Danh sách models hiện có:"
ollama list

echo ""
echo "🚀 Bạn có thể chạy AI service bằng:"
echo "   OLLAMA_MODEL=${MODEL_NAME} uvicorn main:app --reload --port 8000"
