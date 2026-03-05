.PHONY: help install install-dev run test test-coverage clean lint format check docker-build docker-run docker-stop prepare maintenance update-reqs venv

PYTHON := python3
PIP := $(PYTHON) -m pip
SHELL := $(shell which bash)
VENV := .venv
VENV_PYTEST := $(VENV)/bin/pytest
SYSTEM_PYTEST := $(shell which pytest 2>/dev/null)

ifeq ($(wildcard $(VENV_PYTEST)),$(VENV_PYTEST))
    PYTEST := $(VENV_PYTEST)
else ifneq ($(SYSTEM_PYTEST),)
    PYTEST := $(SYSTEM_PYTEST)
else
    PYTEST := pytest
endif

help:
	@echo "Ctx AI - Makefile Commands"
	@echo ""
	@echo "=== Setup ==="
	@echo "  make venv           Create virtual environment"
	@echo "  make install         Install production dependencies"
	@echo "  make install-dev    Install development dependencies"
	@echo "  make setup-dev      Run development setup script"
	@echo "  make prepare        Prepare environment (generate passwords, etc.)"
	@echo ""
	@echo "=== Development ==="
	@echo "  make run            Start the WebUI server"
	@echo "  make test           Run unit tests"
	@echo "  make test-coverage Run tests with coverage report"
	@echo ""
	@echo "=== Code Quality ==="
	@echo "  make lint           Run linting checks"
	@echo "  make format         Format code"
	@echo "  make check          Run all checks (lint + tests)"
	@echo ""
	@echo "=== Docker ==="
	@echo "  make docker-build   Build Docker image"
	@echo "  make docker-run     Run Docker container"
	@echo "  make docker-stop    Stop Docker container"
	@echo ""
	@echo "=== Maintenance ==="
	@echo "  make clean          Clean up cache files"
	@echo "  make maintenance    Run maintenance tool"
	@echo "  make update-reqs   Update requirements versions"

install: venv
	@echo "Installing production dependencies..."
	./$(VENV)/bin/$(PIP) install -r requirements.txt
	./$(VENV)/bin/$(PIP) install -r requirements2.txt

install-dev: venv
	@echo "Installing development dependencies..."
	./$(VENV)/bin/$(PIP) install -r requirements.txt
	./$(VENV)/bin/$(PIP) install -r requirements2.txt
	./$(VENV)/bin/$(PIP) install -r requirements.dev.txt

setup-dev:
	@bash scripts/setup_dev.sh

run: venv
	./$(VENV)/bin/$(PYTHON) run_ui.py

test:
	$(PYTEST) tests/ -v

test-coverage:
	$(PYTEST) tests/ -v --cov=backend --cov-report=html --cov-report=xml

lint:
	@bash scripts/lint.sh check

format:
	@bash scripts/lint.sh fix

check: lint test

clean:
	@bash scripts/clean.sh

docker-build:
	@bash scripts/docker.sh build

docker-run:
	@bash scripts/docker.sh run

docker-stop:
	@bash scripts/docker.sh stop

prepare: venv
	./$(VENV)/bin/$(PYTHON) scripts/prepare.py

maintenance: venv
	./$(VENV)/bin/$(PYTHON) scripts/maintenance_tool.py

update-reqs: venv
	./$(VENV)/bin/$(PYTHON) scripts/update_reqs.py

venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV); \
		echo "Virtual environment created successfully!"; \
	else \
		echo "Virtual environment already exists."; \
	fi
