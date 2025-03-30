.PHONY: setup install clean lint format type-check test test-cov test-ci docs build publish-test publish release help

# Variables
PACKAGE = social_sync
PYTHON = python
POETRY = poetry
PYTEST = $(POETRY) run pytest
PYTEST_COV = $(PYTEST) --cov=$(PACKAGE) --cov-report=term-missing
MYPY = $(POETRY) run mypy
FLAKE8 = $(POETRY) run flake8
BLACK = $(POETRY) run black
ISORT = $(POETRY) run isort
VERSION = $(shell grep "^version" pyproject.toml | cut -d'"' -f2)

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup:  ## Set up development environment
	$(POETRY) install

install:  ## Install the package in development mode
	$(POETRY) install

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

lint:  ## Run linters (flake8)
	$(FLAKE8) src tests

format:  ## Format code with Black and isort
	$(BLACK) src tests
	$(ISORT) src tests

type-check:  ## Run type checking with mypy
	$(MYPY) src

test:  ## Run tests
	$(PYTEST)

test-cov:  ## Run tests with coverage report
	$(PYTEST_COV)
	$(PYTEST_COV) --cov-report=xml

test-ci:  ## Run tests for CI environment
	$(PYTEST_COV) --cov-report=xml

docs:  ## Generate API documentation
	$(POETRY) run pydoc -w src/$(PACKAGE)/*.py
	mkdir -p docs
	mv *.html docs/

build:  ## Build package
	$(POETRY) build

publish-test:  ## Publish to Test PyPI
	$(POETRY) config repositories.testpypi https://test.pypi.org/legacy/
	$(POETRY) publish --repository testpypi

publish:  ## Publish to PyPI
	$(POETRY) publish

release: clean lint type-check test-cov build  ## Prepare a release (run linters, tests, build)
	@echo "Release $(VERSION) ready to publish."
	@echo "To publish, run: make publish"

# Default target
.DEFAULT_GOAL := help