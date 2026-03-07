#!/bin/bash
set -e

# Change to the project root directory
cd "$(dirname "$0")/.."

echo "🧪 Running tests with pytest..."
uv run pytest tests/ "$@"

echo "✅ Tests completed!"
