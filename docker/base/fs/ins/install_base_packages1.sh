#!/bin/bash
set -e

echo "====================BASE PACKAGES1 START===================="

# Retry helper: runs apt-get with --fix-missing on failure to handle unreliable mirrors
apt_with_retry() {
    local attempt=1
    local max_attempts=3
    while [ $attempt -le $max_attempts ]; do
        echo "Attempt $attempt of $max_attempts: $*"
        if "$@"; then
            return 0
        fi
        attempt=$((attempt + 1))
        echo "Retrying with --fix-missing..."
        if "$@" --fix-missing; then
            return 0
        fi
    done
    echo "All attempts failed."
    return 1
}

apt_with_retry apt-get update
apt_with_retry apt-get upgrade -y

apt_with_retry apt-get install -y --no-install-recommends \
    sudo curl wget git cron

apt-get clean && rm -rf /var/lib/apt/lists/*

echo "====================BASE PACKAGES1 END===================="
