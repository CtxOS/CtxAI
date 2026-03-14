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
	docker build -f docker/run/Dockerfile --build-arg BRANCH=dev -t ctxai:latest docker/run

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
	uv run $(RUFF) check src/ tests/

typecheck:
	@echo "Skipping typecheck - run 'make lint' for linting"

format:
	uv run $(RUFF) format src/ tests/
