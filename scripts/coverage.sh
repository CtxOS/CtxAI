#!/bin/bash
set -e

# Change to the project root directory
cd "$(dirname "$0")/.."

echo "📊 Running tests with coverage..."
uv run pytest --cov=src --cov=cli --cov-report=term-missing --cov-report=html tests/ "$@"

echo "✨ Coverage report generated!"
echo "📂 HTML report: htmlcov/index.html"
