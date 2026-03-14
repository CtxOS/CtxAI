#!/bin/bash

. "/ins/setup_venv.sh" "$@"
. "/ins/copy_A0.sh" "$@"

python /ctx/src/ctxai/prepare.py --dockerized=true
# python /ctx/src/ctxai/preload.py --dockerized=true # no need to run preload if it's done during container build

echo "Starting A0..."
exec python /ctx/src/ctxai/run_ui.py \
    --dockerized=true \
    --port=80 \
    --host="0.0.0.0"
