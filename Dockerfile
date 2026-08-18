FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY requirements.txt .
COPY pyproject.toml .
COPY backend/ backend/
COPY frontend/ frontend/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create data directory for ChromaDB persistence
RUN mkdir -p /data

# Expose ports: 8000 for FastAPI, 7860 for Gradio
EXPOSE 8000 7860

# Run startup script
CMD bash -c '\
    export CHROMA_DB_PATH=/data/chroma_db && \
    echo "Starting FastAPI backend..." && \
    python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &> /tmp/backend.log & \
    sleep 5 && \
    echo "Starting Gradio frontend..." && \
    python frontend/app.py \
    '
