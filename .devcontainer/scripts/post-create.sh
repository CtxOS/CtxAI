#!/bin/bash
set -e

echo "🚀 Setting up Ctx AI development environment..."

# Ensure uv cache directory exists
mkdir -p /usr/local/share/uv-cache /usr/local/share/uv-tool-cache

# Install dependencies
echo "📦 Installing dependencies..."
uv sync

# Install development tools
echo "🛠️ Installing development tools..."
uv pip install ruff pytest pytest-asyncio

echo "✅ Setup complete!"
