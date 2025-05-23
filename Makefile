.PHONY: setup install clean lint format type-check test test-cov test-ci docs build publish-test publish release bump-version version-tag pre-commit help

# Path-independent environment setup
SCRIPT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
RUN_SCRIPT := $(SCRIPT_DIR)/scripts/run.sh

# Variables
PACKAGE = bluemastodon
PYTHON = python
POETRY = poetry
POETRY_RUN := $(RUN_SCRIPT)
PYTEST = $(POETRY_RUN) pytest
PYTEST_COV = $(PYTEST) --cov=src/$(PACKAGE) --cov-report=term-missing
MYPY = $(POETRY_RUN) mypy
FLAKE8 = $(POETRY_RUN) flake8
BLACK = $(POETRY_RUN) black
ISORT = $(POETRY_RUN) isort
VERSION = $(shell grep "^version" pyproject.toml | cut -d'"' -f2)

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup:  ## Set up development environment
	$(POETRY) install
	$(POETRY_RUN) pre-commit install
	@echo "Pre-commit hooks installed successfully"

install:  ## Install the package in development mode
	$(POETRY) install
	$(POETRY_RUN) pre-commit install
	@echo "Pre-commit hooks installed successfully"

clean:  ## Remove build artifacts and cache directories
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

lint:  ## Run linters (flake8 and mypy)
	$(FLAKE8) src tests
	$(MYPY) src

format:  ## Format code with Black and isort
	$(BLACK) src tests
	$(ISORT) src tests

type-check:  ## Run type checking with mypy
	$(MYPY) src

pre-commit:  ## Run pre-commit hooks on all files
	$(POETRY_RUN) pre-commit run --all-files

test:  ## Run tests
	$(PYTEST)

test-cov:  ## Run tests with coverage report
	$(PYTEST_COV)
	$(PYTEST_COV) --cov-report=xml

test-ci:  ## Run tests for CI environment
	$(PYTEST_COV) --cov-report=xml

docs:  ## Generate API documentation
	cd $(shell pwd) && PYTHONPATH=$(shell pwd)/src $(POETRY_RUN) python -m pydoc -w bluemastodon
	cd $(shell pwd) && PYTHONPATH=$(shell pwd)/src $(POETRY_RUN) python -m pydoc -w bluemastodon.config bluemastodon.models bluemastodon.bluesky bluemastodon.mastodon bluemastodon.sync
	mkdir -p docs
	mv *.html docs/

build:  ## Build package
	$(POETRY) build

publish-test:  ## Publish to Test PyPI
	$(POETRY) config repositories.testpypi https://test.pypi.org/legacy/
	$(POETRY) publish --repository testpypi

publish:  ## Publish to PyPI
	@echo "NOTICE: For production PyPI publishing, use the GitHub Actions workflow by tagging a release."
	@echo "See CONTRIBUTING.md for the release process."
	@echo ""
	@echo "This command is for emergency manual publishing only."
	@echo "Are you sure you want to publish directly to PyPI? [y/N] "
	@read -r response; \
	if [ "$$response" = "y" ] || [ "$$response" = "Y" ]; then \
		echo "Publishing package to PyPI..."; \
		$(POETRY) publish; \
	else \
		echo "Publishing aborted."; \
	fi

bump-version:  ## Update version in all files (Usage: make bump-version VERSION=x.y.z)
	@if [ -z "$(VERSION)" ]; then \
		echo "Error: VERSION parameter is required"; \
		echo "Usage: make bump-version VERSION=x.y.z"; \
		exit 1; \
	fi
	@echo "Updating version to $(VERSION) in all files..."
	@sed -i.bak 's/^version = ".*"/version = "$(VERSION)"/' pyproject.toml && rm pyproject.toml.bak
	@sed -i.bak 's/__version__ = ".*"/__version__ = "$(VERSION)"/' src/$(PACKAGE)/__init__.py && rm src/$(PACKAGE)/__init__.py.bak
	@sed -i.bak 's/version-[0-9]*\.[0-9]*\.[0-9]*-blue/version-$(VERSION)-blue/' README.md && rm README.md.bak
	@sed -i.bak 's/at version [0-9]*\.[0-9]*\.[0-9]* (beta)/at version $(VERSION) (beta)/' README.md && rm README.md.bak
	@echo "Version updated to $(VERSION) in:"
	@echo "  - pyproject.toml"
	@echo "  - src/$(PACKAGE)/__init__.py"
	@echo "  - README.md"
	@echo ""
	@echo "Don't forget to update CHANGELOG.md with an entry for version $(VERSION)"
	@echo "Then run 'git diff' to verify changes before committing"

version-tag:  ## Create a git tag for the current version
	@echo "Verifying version consistency..."
	@VERSION=$$(grep '^version =' pyproject.toml | sed 's/version = "//;s/"//'); \
	INIT_VERSION=$$(grep '__version__ =' src/$(PACKAGE)/__init__.py | sed 's/__version__ = "//;s/"//'); \
	if [ "$$VERSION" != "$$INIT_VERSION" ]; then \
		echo "Error: Version mismatch! pyproject.toml ($$VERSION) vs __init__.py ($$INIT_VERSION)"; \
		exit 1; \
	fi; \
	echo "Version $$VERSION is consistent across files."

	@echo "Checking for CHANGELOG.md entry..."
	@VERSION=$$(grep '^version =' pyproject.toml | sed 's/version = "//;s/"//'); \
	if ! grep -q "## \[$$VERSION\]" CHANGELOG.md; then \
		echo "Error: No entry for version $$VERSION found in CHANGELOG.md"; \
		exit 1; \
	fi; \
	echo "CHANGELOG.md entry found."

	git tag -a v$(VERSION) -m "Version $(VERSION)"
	@echo "Created tag v$(VERSION). Use 'git push origin v$(VERSION)' to push to remote."

release: clean lint type-check test-cov build  ## Prepare a release (run linters, tests, build)
	@echo "Preparing release process..."

	@echo "Verifying version consistency..."
	@VERSION=$$(grep '^version =' pyproject.toml | sed 's/version = "//;s/"//'); \
	INIT_VERSION=$$(grep '__version__ =' src/$(PACKAGE)/__init__.py | sed 's/__version__ = "//;s/"//'); \
	if [ "$$VERSION" != "$$INIT_VERSION" ]; then \
		echo "Error: Version mismatch! pyproject.toml ($$VERSION) vs __init__.py ($$INIT_VERSION)"; \
		exit 1; \
	fi; \
	echo "Version $$VERSION is consistent across files."

	@echo "Checking for CHANGELOG.md entry..."
	@VERSION=$$(grep '^version =' pyproject.toml | sed 's/version = "//;s/"//'); \
	if ! grep -q "## \[$$VERSION\]" CHANGELOG.md; then \
		echo "Error: No entry for version $$VERSION found in CHANGELOG.md"; \
		exit 1; \
	fi; \
	echo "CHANGELOG.md entry found."

	@echo "Release $(VERSION) ready to publish."
	@echo "To create a tag for this release, run: make version-tag"
	@echo "To push the tag and trigger the GitHub Actions release workflow, run: git push origin v$(VERSION)"

# Default target
.DEFAULT_GOAL := help
