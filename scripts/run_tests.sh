#!/bin/bash
# Run tests with verbose output

cd "$(dirname "$0")/.."

python -m pytest tests/ -v --tb=short "$@"
