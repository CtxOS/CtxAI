#!/bin/bash
# Ensure script exits on error
set -e

echo "=== Cleaning Python caches and pip cache ==="
rm -rf ~/.cache/pip
rm -rf ~/.cache/pypoetry
rm -rf ~/.local/share/virtualenvs

echo "=== Installing project dependencies ==="
if [ -f /workspaces/requirements.txt ]; then
    pip install --no-cache-dir -r /workspaces/requirements.txt
fi

echo "=== Environment ready ==="
