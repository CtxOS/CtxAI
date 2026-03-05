#!/bin/bash
# Clean generated files

cd "$(dirname "$0")/.."

echo "Cleaning up generated files..."

# Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".hypothesis" -exec rm -rf {} + 2>/dev/null || true

# Python bytecode
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name "*.pyd" -delete 2>/dev/null || true

# Coverage
rm -f .coverage coverage.xml 2>/dev/null || true
rm -rf htmlcov 2>/dev/null || true

# IDE
rm -rf .idea .vscode 2>/dev/null || true

# Distribution
rm -rf build dist *.egg-info 2>/dev/null || true

# Logs
rm -rf logs/*.log 2>/dev/null || true

# Temp files
rm -rf tmp/* 2>/dev/null || true

echo "Clean complete!"
