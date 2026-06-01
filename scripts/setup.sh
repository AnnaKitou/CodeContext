#!/bin/bash
# CodeContext Project Setup Script

set -e

echo "🚀 Setting up CodeContext..."

# Check Python version
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "✓ Python version: $PYTHON_VERSION"

# Create .env from .env.example if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your API keys!"
fi

# Install dependencies
echo "📦 Installing dependencies..."
cd backend
uv sync
cd ..

# Create evaluation directories
echo "📁 Creating evaluation directories..."
mkdir -p evaluation
mkdir -p chroma_db

# Initialize ChromaDB (if needed)
echo "✓ Project initialized!"

echo ""
echo "📖 Next steps:"
echo "1. Edit .env with your API keys (ANTHROPIC_API_KEY, GITHUB_TOKEN)"
echo "2. Start backend: cd backend && fastapi dev app/main.py"
echo "3. In another terminal, start frontend: cd frontend && uv run app.py"
echo "4. Open Gradio at http://localhost:7860"
echo ""
