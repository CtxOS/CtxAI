#!/bin/bash
set -e

# this has to be ready from base image
# if [ ! -d /opt/venv ]; then
#     # Create and activate Python virtual environment
#     python3.12 -m venv /opt/venv
#     source /opt/venv/bin/activate
# else
    # source /opt/venv/bin/activate
# fi
if [ ! -d /opt/venv-ctx ]; then
    if [ -d /opt/venv-a0 ]; then
        mv /opt/venv-a0 /opt/venv-ctx
    fi
fi
source /opt/venv-ctx/bin/activate