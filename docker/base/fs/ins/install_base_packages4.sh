#!/bin/bash
set -e

echo "====================BASE PACKAGES4 START===================="

apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-script-latn poppler-utils

apt-get clean && rm -rf /var/lib/apt/lists/*

echo "====================BASE PACKAGES4 END===================="