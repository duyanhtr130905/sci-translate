#!/bin/bash
# Script để tự động hóa việc chuẩn bị model cho Ollama

MODEL_NAME="qwen2.5:3b"

echo "=== AI Service Model Downloader ==="
echo "Checking Ollama connection..."

if ! command -v ollama &> /dev/null
then
    echo "Error: Ollama is not installed on the host."
    exit 1
fi

echo "Pulling model: $MODEL_NAME"
ollama pull $MODEL_NAME

echo "Pulling Embedding model for RAG..."
ollama pull nomic-embed-text

echo "Successfully prepared all models."