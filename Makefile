.PHONY: all init build test test-cov test-cov-html lint lint-fix format check-tools \
       clean clean-cache run-server run-agent \
       docker-base-build docker-run-build docker-run docker-push \
       pypi-build pypi-publish \
       help help-test help-docker help-advanced

# ── Colors ─────────────────────────────────────────────────────────

RED    := \033[0;31m
GREEN  := \033[0;32m
YELLOW := \033[1;33m
BLUE   := \033[0;34m
NC     := \033[0m

# ── Configuration ──────────────────────────────────────────────────

PYTHON  := python
PYTEST  := pytest
RUFF    := ruff
HOST    ?= 0.0.0.0
PORT    ?= 50001

all: help

# ── Utilities ──────────────────────────────────────────────────────

check-tools: ## verify required tools are installed
	@command -v uv >/dev/null 2>&1 || { echo >&2 "$(RED)uv is not installed. Aborting.$(NC)"; exit 1; }
	@echo "$(GREEN)All required tools are installed.$(NC)"

# ── Install ────────────────────────────────────────────────────────

init: check-tools ## install all project dependencies
	@echo "$(GREEN)Installing dependencies...$(NC)"
	uv sync --all-extras
	uv run pre-commit install 2>/dev/null || true
	@echo "$(GREEN)Dependencies installed.$(NC)"

# ── Tests ──────────────────────────────────────────────────────────

test: ## run all tests
	@echo "$(GREEN)Running tests...$(NC)"
	uv run $(PYTEST) $(args)

test-cov: ## run tests with coverage
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	uv run $(PYTEST) --cov --cov-context=test $(args)

test-cov-html: ## run tests with HTML coverage report
	@echo "$(GREEN)Running tests with HTML coverage...$(NC)"
	uv run $(PYTEST) --cov --cov-context=test --cov-report=term-missing --cov-report=html $(args)
	@echo "$(GREEN)Coverage report: htmlcov/index.html$(NC)"

# ── Code Quality ───────────────────────────────────────────────────

lint: ## run linters (ruff check + format check)
	@echo "$(GREEN)Running ruff check...$(NC)"
	uv run $(RUFF) check src/ tests/
	@echo "$(GREEN)Running ruff format check...$(NC)"
	uv run $(RUFF) format --check src/ tests/

lint-fix: ## auto-fix lint issues
	@echo "$(YELLOW)Fixing lint issues...$(NC)"
	uv run $(RUFF) check src/ tests/ --fix
	uv run $(RUFF) format src/ tests/

format: ## format all code
	@echo "$(GREEN)Formatting code...$(NC)"
	uv run $(RUFF) check src/ tests/ --fix
	uv run $(RUFF) format src/ tests/

# ── Server ─────────────────────────────────────────────────────────

run-server: ## start the web UI server
	@echo "$(GREEN)Starting server on $(HOST):$(PORT)...$(NC)"
	uv run python -m ctxai.run_ui

run-agent: ## run agent with a demo task
	@echo "$(GREEN)Starting agent...$(NC)"
	uv run ctxai --debug agent --profile default --task "Analyze local log files"

# ── Docker ─────────────────────────────────────────────────────────

docker-base-build: ## build base Docker image
	docker build -f docker/base/Dockerfile -t ctxos/ctxai-base docker/base

docker-run-build: ## build runtime Docker image
	docker build --file DockerfileLocal --build-arg BRANCH=local -t ctxai:latest .

docker-run: docker-run-build ## build and run Docker container
	@echo "$(GREEN)Running container on port $(PORT)...$(NC)"
	docker run -p $(PORT):80 ctxai:latest

docker-push: ## push Docker image to registry
	docker tag ctxai:latest ctxos/ctxai:latest
	docker push ctxos/ctxai:latest

# ── Publish ────────────────────────────────────────────────────────

pypi-build: ## build Python package
	uv build

pypi-publish: ## publish to PyPI
	uv publish

# ── Clean ──────────────────────────────────────────────────────────

clean: clean-cache ## remove build artifacts
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	rm -rf build/ dist/ *.egg-info htmlcov/ .coverage .pytest_cache/

clean-cache: ## remove Python cache files
	@echo "$(YELLOW)Cleaning cache...$(NC)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# ── Help ───────────────────────────────────────────────────────────

help: ## show this help message
	@echo ''
	@echo "$(GREEN)══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)                      CTX AI COMMANDS                        $(NC)"
	@echo "$(GREEN)══════════════════════════════════════════════════════════════$(NC)"
	@echo ''
	@echo "$(GREEN)Setup:$(NC)"
	@echo "  $(GREEN)make init$(NC)              - Install all dependencies"
	@echo "  $(GREEN)make check-tools$(NC)       - Verify required tools"
	@echo ''
	@echo "$(GREEN)Testing:$(NC)"
	@echo "  $(GREEN)make test$(NC)              - Run all tests"
	@echo "  $(GREEN)make test-cov$(NC)          - Run tests with coverage"
	@echo "  $(GREEN)make test-cov-html$(NC)     - Run tests with HTML coverage"
	@echo "  $(GREEN)make test args='-x'$(NC)    - Run tests with extra pytest args"
	@echo ''
	@echo "$(GREEN)Code Quality:$(NC)"
	@echo "  $(GREEN)make lint$(NC)              - Run linters (ruff check + format)"
	@echo "  $(GREEN)make lint-fix$(NC)          - Auto-fix lint issues"
	@echo "  $(GREEN)make format$(NC)            - Format all code"
	@echo ''
	@echo "$(GREEN)Run:$(NC)"
	@echo "  $(GREEN)make run-server$(NC)        - Start web UI ($(HOST):$(PORT))"
	@echo "  $(GREEN)make run-agent$(NC)         - Run agent demo task"
	@echo ''
	@echo "$(GREEN)Docker:$(NC)"
	@echo "  $(GREEN)make docker-base-build$(NC) - Build base image"
	@echo "  $(GREEN)make docker-run-build$(NC)  - Build runtime image"
	@echo "  $(GREEN)make docker-run$(NC)        - Build and run container"
	@echo "  $(GREEN)make docker-push$(NC)       - Push to registry"
	@echo ''
	@echo "$(GREEN)Publish:$(NC)"
	@echo "  $(GREEN)make pypi-build$(NC)        - Build Python package"
	@echo "  $(GREEN)make pypi-publish$(NC)      - Publish to PyPI"
	@echo ''
	@echo "$(GREEN)Clean:$(NC)"
	@echo "  $(GREEN)make clean$(NC)             - Remove build artifacts"
	@echo "  $(GREEN)make clean-cache$(NC)       - Remove Python cache"
	@echo ''
	@echo "$(GREEN)══════════════════════════════════════════════════════════════$(NC)"
	@echo ''
