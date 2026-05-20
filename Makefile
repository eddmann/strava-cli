.PHONY: *
.DEFAULT_GOAL := help

SHELL := /bin/bash
VERSION := $(shell grep '^version' pyproject.toml | cut -d '"' -f 2)

##@ Setup

deps: ## Install dependencies
	@uv sync

deps/prod: ## Install production dependencies only
	@uv sync --no-dev

install: deps

update: ## Update all dependencies to latest versions
	@uv lock --upgrade
	@uv sync

lock: ## Regenerate lock file from scratch
	@rm -f uv.lock
	@uv lock

clean: ## Clean up cache files and build artifacts
	@rm -rf .pytest_cache/ .ruff_cache/ .mypy_cache/ .pyright/
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@rm -rf dist/ build/ *.egg-info/

##@ Testing/Linting

can-release: lint test ## Run all the same checks as CI to ensure code can be released

test: ## Run the test suite
	@uv run python -m pytest

test/%: ## Run a single test path (e.g., make test/test_cli.py::test_name)
	@uv run python -m pytest tests/$* -v

test/verbose: ## Run tests with verbose output
	@uv run python -m pytest -v

test/coverage: ## Run tests with coverage report
	@uv run python -m pytest --cov=src/strava_cli --cov-report=term-missing

lint: lint/ruff lint/pyright ## Run all linting tools

lint/ruff: ## Run ruff linter
	@uv run ruff check
	@uv run ruff format --check

lint/pyright: ## Run pyright type checker
	@uv run python -m pyright

fmt: format
format: ## Fix style violations and format code
	@uv run ruff check --fix
	@uv run ruff format

##@ Packaging

set-version: ## Set version (VERSION=x.x.x)
	@sed -i.bak 's/^version = "[^"]*"/version = "$(VERSION)"/' pyproject.toml
	@sed -i.bak 's/__version__ = "[^"]*"/__version__ = "$(VERSION)"/' src/strava_cli/__init__.py
	@rm -f pyproject.toml.bak src/strava_cli/__init__.py.bak

build: clean ## Build source and wheel distributions
	@uv build

package/check: build ## Validate built distributions
	@uvx twine check dist/*

binary: clean ## Build standalone binary
	@uv run pyinstaller \
		--onefile \
		--name strava \
		--distpath dist \
		--specpath build \
		--workpath build/work \
		src/strava_cli/cli.py

##@ Development

auth: ## Run the Strava authentication setup
	@uv run strava auth login

run: ## Run a strava command (CMD="activities list")
	@uv run strava $(CMD)

shell: ## Open a Python shell with the project context
	@uv run python

##@ Info

version: ## Show current version
	@echo $(VERSION)

deps/list: ## Show installed dependencies
	@uv pip list

info: ## Show project information
	@echo "Project: strava-cli"
	@echo "Version: $(VERSION)"
	@echo "Python: $$(python --version)"

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_\-\/]+:.*?##/ { printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

t: test
