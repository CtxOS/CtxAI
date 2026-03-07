#!/bin/bash
set -e

# Change to the project root directory
cd "$(dirname "$0")/.."

echo "🔍 Linting Python files with Ruff..."
uv run ruff check .

# echo "🧐 Type checking with Mypy..."
# uv run mypy .

echo "✅ Linting complete!"
