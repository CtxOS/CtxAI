#!/bin/bash

# Wait until run_tunnel.py exists
echo "Starting tunnel API..."

sleep 1
while [ ! -f /ctx/src/ctxai/run_tunnel.py ]; do
    echo "Waiting for /ctx/src/ctxai/run_tunnel.py to be available..."
    sleep 1
done

. "/ins/setup_venv.sh" "$@"

exec python /ctx/src/ctxai/run_tunnel.py \
    --dockerized=true \
    --port=80 \
    --tunnel_api_port=55520 \
    --host="0.0.0.0"
