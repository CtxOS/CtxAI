#!/bin/bash
set -e

echo "====================BASE PACKAGES3 START===================="

apt-get update && apt-get install -y --no-install-recommends \
    nodejs npm

apt-get clean && rm -rf /var/lib/apt/lists/*

echo "====================BASE PACKAGES3 NPM===================="

# we shall not install npx separately, it's discontinued and some versions are broken
# npm i -g npx
echo "====================BASE PACKAGES3 END===================="
