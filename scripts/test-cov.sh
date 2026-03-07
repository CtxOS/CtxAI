#!/bin/bash
set -e

# Change to the project root directory
cd "$(dirname "$0")/.."

echo "🧪 Running tests with coverage..."
uv run pytest --cov=src --cov=cli --cov-report=term-missing --cov-report=xml --cov-report=html tests/ "$@"

echo "✅ Tests and coverage report completed!"
