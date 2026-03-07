# Ctx AI Makefile

# Variables
UV = uv
PYTHON = $(UV) run python
CTXAI = $(UV) run ctxai
DOCKER_IMAGE = ctxai-local
CACHE_DATE = $(shell date +%Y-%m-%d:%H:%M:%S)

.PHONY: all install build run test docker deploy clean help

all: help

help:
	@echo "Ctx AI Management Commands:"
	@echo "  install      Install the project in editable mode"
	@echo "  run          Start the Web UI"
	@echo "  agent-list   List available agents"
	@echo "  doctor       Diagnose the environment"
	@echo "  test         Run tests"
	@echo "  coverage     Run tests with coverage"
	@echo "  lint         Check code style"
	@echo "  format       Format code"
	@echo "  docker       Build the local development image"
	@echo "  reset        Reset runtime state (logs/tmp)"
	@echo "  clean        Remove caches and temporary files"

install:
	$(UV) sync
	$(UV) run playwright install chromium

run:
	$(CTXAI) ui start

agent-list:
	$(CTXAI) agent list

doctor:
	$(CTXAI) dev doctor

test:
	./scripts/test.sh

coverage:
	./scripts/test-cov.sh

lint:
	./scripts/lint.sh

format:
	./scripts/format.sh

docker:
	docker build -f Dockerfile.local -t $(DOCKER_IMAGE) --build-arg CACHE_DATE=$(CACHE_DATE) .

docker-base:
	docker build -t ctxai-base:local -f docker/base/Dockerfile --build-arg CACHE_DATE=$(CACHE_DATE) docker/base

deploy-base:
	@echo "Deploying base image to DockerHub..."
	docker buildx build -f docker/base/Dockerfile -t ctxos/ctxai-base:latest --platform linux/amd64,linux/arm64 --push --build-arg CACHE_DATE=$(CACHE_DATE) docker/base

deploy:
	@echo "Deploying latest version to DockerHub..."
	docker buildx build -f docker/run/Dockerfile -t ctxos/ctxai:latest --platform linux/amd64,linux/arm64 --push --build-arg BRANCH=main --build-arg CACHE_DATE=$(CACHE_DATE) docker/run

reset:
	rm -rf data/tmp/*
	rm -rf data/logs/*
	@echo "Runtime state reset."

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .uv
	rm -rf data/logs/*.html
	@echo "Cleaned up temporary files and caches."
