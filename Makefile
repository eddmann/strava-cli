.DEFAULT_GOAL := help

.PHONY: *

help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z\/_%-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

install: ## Install package in development mode
	uv sync --all-extras

run: ## Run a strava command (CMD="activities list")
	uv run strava $(CMD)

##@ Testing/Linting

can-release: lint test ## Run all CI checks (lint + test)

lint: ## Run ruff linter and format check
	uv run ruff check src tests
	uv run ruff format --check src tests

fmt: ## Format code with ruff
	uv run ruff format src tests
	uv run ruff check --fix src tests

test: ## Run all tests
	uv run pytest

test/%: ## Run a single test (e.g., make test/test_cli.py::test_name)
	uv run pytest tests/$* -v

##@ Build/Release

set-version: ## Set version (VERSION=x.x.x)
	sed -i.bak 's/version = "[^"]*"/version = "$(VERSION)"/' pyproject.toml
	sed -i.bak 's/__version__ = "[^"]*"/__version__ = "$(VERSION)"/' src/strava_cli/__init__.py
	rm -f pyproject.toml.bak src/strava_cli/__init__.py.bak

build: ## Build standalone binary
	uv run pyinstaller \
		--onefile \
		--name strava \
		--distpath dist \
		--specpath build \
		--workpath build/work \
		src/strava_cli/cli.py

dist: ## Build wheel/sdist for PyPI
	uv build

clean: ## Clean build artifacts
	rm -rf dist/ build/ *.egg-info/ .pytest_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

##@ Utilities

check-version: ## Show current version
	@grep 'version = ' pyproject.toml | head -1
	@uv run python -c "from strava_cli import __version__; print(f'Code version: {__version__}')"
