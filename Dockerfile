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
RUN mkdir -p /data && chmod 777 /data
ENV CHROMA_DB_PATH=/data/chroma_db

# HF Spaces routes traffic to app_port 7860 — FastAPI serves both the API
# and the custom HTML frontend (frontend/index.html) at "/"
EXPOSE 7860

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "7860"]
