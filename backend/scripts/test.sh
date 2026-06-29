#!/usr/bin/env bash
# Run the full test suite with coverage — mirrors the template's test.sh
set -e
set -x

cd "$(dirname "$0")/.."   # run from backend/

coverage run --source=app -m pytest
coverage report --show-missing
coverage html --title "CodeContext Coverage"
