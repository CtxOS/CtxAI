#!/bin/bash

. "/ins/setup_venv.sh" "$@"
. "/ins/copy_CTX0.sh" "$@"

echo "Starting CTX0 bootstrap manager..."
exec python /exe/self_update_manager.py docker-run-ui
