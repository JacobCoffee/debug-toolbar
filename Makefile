.DEFAULT_GOAL := help
.PHONY: help install dev install-uv lint lint-fix fmt fmt-check type-check test test-cov test-fast test-parallel test-parallel-fast test-debug test-failed ci docs docs-serve docs-clean build clean destroy prek-install prek-run prek-update lock upgrade wt worktree wt-ls worktree-list wt-j worktree-jump worktree-prune ci-install example example-asgi example-litestar example-aa example-graphql example-mcp example-mcp-server act act-ci act-test

# ==================================================================================== #
# VARIABLES
# ==================================================================================== #

SRC_DIR := src
TEST_DIR := tests
DOCS_DIR := docs

# ==================================================================================== #
# HELP
# ==================================================================================== #

help: ## Show this help message
	@echo 'Usage:'
	@echo '  make <target>'
	@echo ''
	@awk 'BEGIN {FS = ":.*##"; printf ""} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ Installation

install: ## Install package in production mode
	@uv sync

dev: ## Install package with all development dependencies
	@uv sync --all-extras

install-uv: ## Install latest version of uv
	@curl -LsSf https://astral.sh/uv/install.sh | sh

##@ Code Quality

lint: ## Run ruff linter
	@uv run ruff check $(SRC_DIR) $(TEST_DIR)

lint-fix: ## Run ruff linter with auto-fix
	@uv run ruff check --fix $(SRC_DIR) $(TEST_DIR)

fmt: ## Format code with ruff
	@uv run ruff format $(SRC_DIR) $(TEST_DIR)

fmt-check: ## Check code formatting without changes
	@uv run ruff format --check $(SRC_DIR) $(TEST_DIR)

type-check: ## Run type checking with ty
	@uv run ty check $(SRC_DIR)

##@ Testing

test: ## Run test suite
	@PYTHONDONTWRITEBYTECODE=1 uv run pytest

test-cov: ## Run tests with coverage report
	@PYTHONDONTWRITEBYTECODE=1 uv run pytest --cov=debug_toolbar --cov-report=term-missing --cov-report=html --cov-report=xml

test-fast: ## Run tests without slow/integration tests
	@PYTHONDONTWRITEBYTECODE=1 uv run pytest -m "not integration"

test-parallel: ## Run tests in parallel with pytest-xdist
	@PYTHONDONTWRITEBYTECODE=1 uv run pytest -n auto

test-parallel-fast: ## Run unit tests in parallel
	@PYTHONDONTWRITEBYTECODE=1 uv run pytest -n auto -m "not integration"

test-debug: ## Run tests with verbose output and no capture
	@PYTHONDONTWRITEBYTECODE=1 uv run pytest -vv -s

test-failed: ## Re-run only failed tests from last run
	@PYTHONDONTWRITEBYTECODE=1 uv run pytest --lf

##@ Documentation

docs: ## Build documentation
	@uv run sphinx-build -b html $(DOCS_DIR) $(DOCS_DIR)/_build/html

docs-serve: ## Serve documentation with live reload
	@uv run sphinx-autobuild $(DOCS_DIR) $(DOCS_DIR)/_build/html --open-browser --port 8080

docs-clean: ## Clean built documentation
	@rm -rf $(DOCS_DIR)/_build

##@ Build & Release

build: clean ## Build package distributions
	@uv build

clean: ## Clean build artifacts and caches
	@rm -rf __pycache__
	@rm -rf .pytest_cache
	@rm -rf .mypy_cache
	@rm -rf .ruff_cache
	@rm -rf dist
	@rm -rf build
	@rm -rf *.egg-info
	@rm -rf src/*.egg-info
	@rm -rf htmlcov
	@rm -rf .coverage
	@rm -rf coverage.xml
	@find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name '*.pyc' -delete 2>/dev/null || true
	@find . -type f -name '*.pyo' -delete 2>/dev/null || true

destroy: clean docs-clean ## Remove virtual environment and all artifacts
	@rm -rf .venv

##@ Development

prek-install: ## Install prek hooks
	@uv run prek install
	@uv run prek install --hook-type commit-msg
	@uv run prek install --hook-type pre-push

prek-run: ## Run prek on all files
	@uv run prek run --all-files

prek-update: ## Update prek hooks
	@uv run prek autoupdate

lock: ## Update lock file
	@uv lock

upgrade: ## Upgrade all dependencies
	@uv lock --upgrade

##@ Examples

example: example-litestar ## Alias for example-litestar

example-asgi: ## Run ASGI example app (http://localhost:8000)
	@uv run examples/asgi_basic/app.py

example-litestar: ## Run Litestar example app (http://localhost:8001)
	@uv run examples/litestar_basic/app.py

example-aa: ## Run Litestar + Advanced-Alchemy example (http://localhost:8002)
	@uv run examples/litestar_advanced_alchemy/app.py

example-graphql: ## Run GraphQL + Strawberry example (http://localhost:8003)
	@uv run examples/graphql_panel_example.py

example-mcp: ## Run MCP server example (http://localhost:8004)
	@uv run examples/mcp_server_example.py

example-mcp-server: ## Run MCP server (stdio transport)
	@uv run examples/mcp_server_example.py --mcp

##@ Git Worktrees

wt: worktree ## Alias for worktree
worktree: ## Create a new git worktree (Usage: make wt NAME=my-feature)
	@if [ -z "$(NAME)" ]; then \
		echo "Error: NAME variable is required. Usage: make wt NAME=feature-name"; \
		exit 1; \
	fi
	@mkdir -p .worktrees
	@git worktree add -b $(NAME) .worktrees/$(NAME) main
	@echo "Created worktree at .worktrees/$(NAME)"

wt-ls: worktree-list ## Alias for worktree-list
worktree-list: ## List all git worktrees
	@git worktree list

wt-j: worktree-jump ## Alias for worktree-jump
worktree-jump: ## Jump to a worktree (Usage: cd $(make wt-j NAME=foo) or make wt-j to list)
	@if [ -z "$(NAME)" ]; then \
		echo "Available worktrees:"; \
		@git worktree list --porcelain | grep "^worktree" | cut -d' ' -f2; \
		echo ""; \
		echo "Usage: cd \$$(make wt-j NAME=<name>)"; \
	else \
		path=".worktrees/$(NAME)"; \
		if [ -d "$$path" ]; then \
			echo "$$path"; \
		else \
			echo "Worktree not found: $$path" >&2; \
			exit 1; \
		fi; \
	fi

worktree-prune: ## Clean up stale git worktrees
	@git worktree prune
	@echo "Pruned stale worktrees"

##@ CI Helpers

ci: lint fmt type-check test-parallel-fast docs ## Run all CI checks locally (excludes integration tests, runs in parallel)

ci-install: ## Install for CI (frozen dependencies)
	@uv sync --all-extras --frozen

act: ## Run GitHub Actions locally with act
	@act -l

act-ci: ## Run CI workflow locally with act
	@act push -j lint-format-typecheck -j smoke-test -j test

act-test: ## Run test job locally with act
	@act push -j test --matrix python-version:3.12 --matrix os:ubuntu-latest
