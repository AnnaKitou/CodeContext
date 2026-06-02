#!/usr/bin/env bash
# Run all linters — mirrors the template's lint.sh
set -e
set -x

cd "$(dirname "$0")/.."   # run from backend/

mypy app
uv run ty check app
ruff check app
ruff format app --check
