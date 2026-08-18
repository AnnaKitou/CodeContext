#!/bin/bash

# HF Spaces startup script - runs backend + frontend

# Use persistent /data directory on HF Spaces if available
if [ -d "/data" ]; then
    export CHROMA_DB_PATH="/data/chroma_db"
    echo "Using HF Spaces persistent storage: $CHROMA_DB_PATH"
else
    export CHROMA_DB_PATH="./chroma_db"
    echo "Using local ChromaDB path: $CHROMA_DB_PATH"
fi

# Start FastAPI backend in background
echo "Starting FastAPI backend..."
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 5

# Start Gradio frontend
echo "Starting Gradio frontend..."
python frontend/app.py
