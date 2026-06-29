#!/usr/bin/env bash
# Auto-format code — mirrors the template's format.sh
set -e
set -x

cd "$(dirname "$0")/.."   # run from backend/

ruff check app --fix
ruff format app
