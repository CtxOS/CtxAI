.PHONY: build test docker-base-build docker-run-build docker-push pypi-build pypi-publish clean lint typecheck

PYTHON := python
PYTEST := pytest
RUFF := ruff

build:
	uv sync

test:
	uv run $(PYTEST)

docker-base-build:
	docker build -f docker/base/Dockerfile -t ctxos/ctxai-base docker/base

docker-run-build:
	docker build --file DockerfileLocal --build-arg BRANCH=local -t ctxai:latest .

docker-push:
	docker tag ctxai:latest ctxos/ctxai:latest
	docker push ctxos/ctxai:latest

pypi-build:
	uv build

pypi-publish:
	uv publish

clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

lint:
	uvx $(RUFF) check src/ tests/

typecheck:
	@echo "Skipping typecheck - run 'make lint' for linting"

format:
	uvx $(RUFF) format src/ tests/

# --- CLI Shortcuts ---
run-server:
	uv run ctxai server --host 0.0.0.0 --port 8000

These changes ensure that all references to the container's root directory are updated to `/ctx/`. Let me know if you have any other questions!

<!--
[PROMPT_SUGGESTION]How do I add a new tool to the framework?[/PROMPT_SUGGESTION]
[PROMPT_SUGGESTION]Explain the purpose of the `uv.lock` file.[/PROMPT_SUGGESTION]
-->

run-agent:
	uv run ctxai --debug agent --profile default --task "Analyze local log files"

help:
	uv run ctxai --help
