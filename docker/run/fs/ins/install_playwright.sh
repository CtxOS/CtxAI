#!/bin/bash
set -e

# activate venv
. "/ins/setup_venv.sh" "$@"

# playwright is already in requirements.txt, skip re-installation
# uv pip install playwright

# set PW installation path to /ctx/tmp/playwright
export PLAYWRIGHT_BROWSERS_PATH=/ctx/tmp/playwright

# install chromium with dependencies
apt-get install -y fonts-unifont libnss3 libnspr4 libatk1.0-0 libatspi2.0-0 libxcomposite1 libxdamage1 libatk-bridge2.0-0 libcups2
playwright install chromium --only-shell
