#!/usr/bin/env bash

set -e
set -x

export PYTHONPATH=./src
pytest -n auto --dist loadgroup ${@}