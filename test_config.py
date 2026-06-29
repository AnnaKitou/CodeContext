#!/usr/bin/env python3
"""Test script to debug config loading."""

from pathlib import Path
import os
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Check .env file exists
env_file = Path(__file__).parent / ".env"
print(f"[CHECK] .env file exists: {env_file.exists()}")

# Check environment variables before importing settings
print("\n[BEFORE] Environment variables:")
print(f"  ANTHROPIC_API_KEY set: {'ANTHROPIC_API_KEY' in os.environ}")
print(f"  GITHUB_TOKEN set: {'GITHUB_TOKEN' in os.environ}")

# Now load settings
from app.core.config import settings

print("\n[AFTER] Settings loaded:")
print(f"  anthropic_api_key: {settings.anthropic_api_key[:20] if settings.anthropic_api_key else 'NOT SET'}...")
print(f"  anthropic_model: {settings.anthropic_model}")
print(f"  github_token: {settings.github_token[:20] if settings.github_token else 'NOT SET'}...")
print(f"  github_repo_owner: {settings.github_repo_owner}")
print(f"  debug: {settings.debug}")
print(f"  port: {settings.port}")
