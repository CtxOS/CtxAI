#!/bin/bash
set -e

echo "====================BASE PACKAGES1 START===================="

apt-get update && apt-get upgrade -y

apt-get install -y --no-install-recommends \
    sudo curl wget git cron

apt-get clean && rm -rf /var/lib/apt/lists/*

echo "====================BASE PACKAGES1 END===================="
