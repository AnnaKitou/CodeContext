# ── CodeContext — Docker image (Hugging Face Spaces / any container host) ──────
# The app clones git repos at runtime, builds a ChromaDB vector index on disk,
# and serves both the REST API and the web UI from FastAPI.

FROM python:3.11-slim

# git is REQUIRED at runtime — the /ingest endpoint shells out to `git clone`.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# uv (fast dependency manager) — copied from the official image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Hugging Face Spaces runs the container as a non-root user with UID 1000.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

# Install dependencies first (better layer caching), then the rest of the source.
COPY --chown=user pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=user . /app
RUN uv sync --frozen --no-dev

# Writable, predictable locations for the vector store and temporary clones.
# Use /home/user for persistent storage across container restarts in HF Spaces.
ENV CHROMA_DB_PATH=/home/user/.chroma_db \
    PORT=7860

EXPOSE 7860

# Bind to 0.0.0.0 on the HF Spaces port. --app-dir puts `backend/` on sys.path
# so `app.main:app` resolves and the frontend/ folder is found relative to it.
CMD ["uv", "run", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "7860"]
