#!/bin/bash
set -e

# Change to the project root directory
cd "$(dirname "$0")/.."

echo "🚀 Formatting Python files with Ruff..."
uv run ruff check --select I --fix .  # Sort imports
uv run ruff check --fix .            # Lint and fix
uv run ruff format .                 # Format code

echo "✨ Formatting complete!"
