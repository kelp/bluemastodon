# Social-Sync Project Guidelines

## Project Overview
A Python application to automatically cross-post manual Bluesky posts to Mastodon using GitHub Actions.

**Scope**: This tool specifically handles synchronizing manual posts from Bluesky to Mastodon. Blog post publishing to social platforms will be managed by a separate tool in the blog repository.

## Architecture
1. **Modular Structure**:
   - `bluesky.py`: Handles Bluesky API interactions
   - `mastodon.py`: Handles Mastodon API interactions
   - `sync.py`: Core sync logic and orchestration
   - `config.py`: Configuration management
   - `models.py`: Data models/schemas

2. **Documentation**:
   - Docstrings for all public methods/classes following Google style
   - Module-level docstrings explaining purpose
   - Type hints throughout
   - Examples in docstrings where helpful
   - README with setup and usage instructions
   - Generated documentation with pydoc

3. **Testing**:
   - Pytest for unit and integration tests
   - 100% test coverage with pytest-cov
   - Mock external API calls

4. **Quality Standards**:
   - Black for code formatting
   - Isort for import sorting
   - Flake8 for linting
   - Mypy for type checking
   - Methods under 30 lines
   - Pydocstyle for docstring checking
   - Bandit for security linting
   - Pre-commit hooks to enforce standards

5. **CI/CD**:
   - GitHub Actions for testing/linting
   - Scheduled job for cross-posting

6. **Error Handling**:
   - Robust error handling and logging
   - Retries for API failures

## Commands
- Format code: `black . && isort .`
- Lint: `flake8`
- Type check: `mypy .`
- Run tests: `pytest`
- Check coverage: `pytest --cov=src --cov-report=term-missing`
- Generate docs: `pydoc -w src/*.py`

## Coding Standards
- Follow PEP 8 style guide
- Keep methods under 30 lines where reasonable
- Use type hints for all function parameters and return values
- 100% test coverage required
- Descriptive variable and function names
- Isolate dependencies and use dependency injection
- Proper error handling with specific exceptions