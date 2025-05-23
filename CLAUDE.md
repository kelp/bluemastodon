# BlueMastodon Project Guidelines

## Code Quality Automation

The repository uses pre-commit hooks to automatically ensure code quality before each commit.
The pre-commit hooks handle:

- Code formatting (black, isort)
- Linting (flake8)
- Type checking (mypy)
- Security scanning (bandit)
- Test coverage (pytest with 90% coverage requirement)

All quality checks run automatically before each commit, preventing commits that would fail CI.

To manually run all checks:
```bash
pre-commit run --all-files
```

## Project Overview
A Python application to automatically cross-post manual Bluesky posts to
Mastodon using GitHub Actions.

**Scope**: This tool specifically handles synchronizing manual posts from
Bluesky to Mastodon. Blog post publishing to social platforms will be
managed by a separate tool in the blog repository.

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
   - 90% test coverage with pytest-cov
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
- 90% test coverage required
- Descriptive variable and function names
- Isolate dependencies and use dependency injection
- Proper error handling with specific exceptions

## API Documentation

### Mastodon API
- Documentation: [Mastodon API Intro](https://docs.joinmastodon.org/client/intro/)
- REST API using HTTP requests and JSON responses
- Supports various parameter formats including query strings, form data, and JSON
- Authentication via OAuth
- Standard HTTP status codes (200 for success, 4xx for client errors, 5xx for server errors)

### Bluesky/AT Protocol
- Documentation: [atproto Python Library](https://atproto.blue/en/latest/)
- Comprehensive Python SDK for AT Protocol and Bluesky
- Supports both synchronous and asynchronous API interactions
- Features include authentication, posting, following, likes, etc.
- Example usage:
  ```python
  from atproto import Client

  client = Client()
  client.login('username', 'password')
  client.send_post(text='Hello World!')
  ```

## Makefile Commands
- Run tests: `make test`
- Run linters: `make lint`
- Tag a release: `make release`
- Bump versions: `make bump-version`
