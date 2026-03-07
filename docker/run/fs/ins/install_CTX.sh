#!/bin/bash
set -e

# Exit immediately if a command exits with a non-zero status.
# set -e

# branch from parameter
if [ -z "$1" ]; then
    echo "Error: Branch parameter is empty. Please provide a valid branch name."
    exit 1
fi
BRANCH="$1"

if [ "$BRANCH" = "local" ]; then
    # For local branch, use the files
    echo "Using local dev files in /git/ctxai"
    # List all files recursively in the target directory
    # echo "All files in /git/ctxai (recursive):"
    # find "/git/ctxai" -type f | sort
else
    # For other branches, clone from GitHub
    echo "Cloning repository from branch $BRANCH..."
    git clone -b "$BRANCH" "https://github.com/ctxos/ctxai" "/git/ctxai" || {
        echo "CRITICAL ERROR: Failed to clone repository. Branch: $BRANCH"
        exit 1
    }
fi

. "/ins/setup_venv.sh" "$@"

# moved to base image
# # Ensure the virtual environment and pip setup
# pip install --upgrade pip ipython requests
# # Install some packages in specific variants
# pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install CTX python packages
export UV_MAX_RETRIES=10
export UV_HTTP_TIMEOUT=300
uv pip install -e /git/ctxai

# install playwright
bash /ins/install_playwright.sh "$@"

# Preload CTX
python3 -m ctxai.core.preload --dockerized=true
