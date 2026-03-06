#!/bin/bash
# Code linting and formatting

cd "$(dirname "$0")/.."

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

ACTION=${1:-check}

case "$ACTION" in
    check)
        echo "Running linting checks..."
        flake8 backend/ --max-line-length=100 --ignore=E501,W503,E203,E402,W605,F541,F811,E722,E704,F841,F824,E713,E226,W291,F401 || true
        ;;
    fix)
        echo "Fixing linting issues..."
        black backend/ --line-length=100
        isort backend/
        ;;
    *)
        echo "Usage: $0 [check|fix]"
        exit 1
        ;;
esac
