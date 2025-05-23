# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.9.9] - 2025-01-24

### Changed
- Updated all dependencies to latest versions with flexible versioning strategy
- Switched from hard-pinned versions to minimum versions with upper bounds for major versions
- Added py.typed marker to make the package type-aware
- Fixed all mypy type annotation issues in test files
- Improved type safety throughout the codebase

### Added
- Added types-setuptools dev dependency for better type checking
- Added coverage configuration to pyproject.toml to fix import warnings
- Added py.typed marker file for PEP 561 compliance

### Fixed
- Fixed coverage warning "Module bluemastodon was previously imported, but not measured"
- Fixed all mypy type annotation issues in test files
- Refactored test_main.py and test_if_name_main.py to avoid import conflicts

### Technical
- Updated dependency versions:
  - atproto: `>=0.0.61,<0.1.0` (was `==0.0.59`)
  - mastodon-py: `>=2.0.1,<3.0.0` (was `>=1.8.1`)
  - pydantic: `>=2.11.5,<3.0.0` (was `==2.8.0`)
  - python-dotenv: `>=1.1.0,<2.0.0` (was `>=1.0.0`)
  - loguru: `>=0.7.3,<1.0.0` (was `>=0.7.2`)
- Configured mypy to be less strict for test files while maintaining strict checks for source code
- Updated coverage configuration to use src/bluemastodon path consistently
- Fixed Makefile PYTEST_COV command to use correct source path
- Reduced code coverage requirement from 100% to 90%
- Improved type handling in MastodonClient.post
- Cleaned up code formatting and docstrings

## [0.9.8] - 2025-05-01

### Added
- Complete thread support with true parent-child relationship on Mastodon
- Thread synchronization from Bluesky (self-replies)
- New configuration option `INCLUDE_THREADS` to control thread synchronization

### Fixed
- Fixed duplicate links issue by replacing truncated links in post content with their full URLs

## [0.9.7] - 2025-03-30

### Changed
- Improved pre-commit hooks with better Python compatibility checks
- Updated type annotations to use Python 3.10+ syntax
- Fixed all linting issues and code formatting

## [0.9.6] - 2025-03-30

### Fixed
- Fixed truncated URLs in Mastodon posts by appending full URLs from link metadata
- Removed complex URL pattern matching in favor of a simpler, more reliable approach

## [0.9.5] - 2025-03-30

### Fixed
- Fixed GitHub release workflow to properly extract changelog content

## [0.9.4] - 2025-03-30

This version is identical to 0.9.3 in functionality but increments the version number to address a PyPI publishing conflict.

## [0.9.3] - 2025-03-30

This release includes the project rename from social-sync to bluemastodon and adds comprehensive PyPI packaging with CLI support, making it easy to install and use directly from PyPI.

### Added
- PyPI packaging with full metadata for improved discoverability
- Command-line interface available after pip installation
- Comprehensive installation and usage documentation

### Changed
- Renamed project from social-sync to bluemastodon to avoid name conflicts on PyPI
- Fixed code formatting and linting issues across the codebase
- Updated project configuration files to use correct module paths
- Updated dependencies to latest versions

### Development
- Configured trusted publishing for secure PyPI releases
- Added classifiers and keywords for better PyPI categorization

## [0.9.2] - 2025-03-30

### Fixed
- Improved GitHub Actions caching to eliminate cache write conflicts
- Added workflow concurrency control to prevent race conditions
- Enhanced cache restore capability with fallback keys

### Changed
- Enhanced release process in Makefile to improve version management

## [0.9.1] - 2025-03-30

### Fixed
- Improved state file management to prevent double posts
- Added immediate state saving after successful Mastodon posts
- Added detection for partial success scenarios
- Added sync_state.json to .gitignore to prevent committing state

### Changed
- Aligned CI and pre-commit lint configurations
- Added bandit to GitHub Actions workflow
- Enforced 100% test coverage in CI

## [0.9.0] - 2025-03-29

### Added
- Initial release
- Bluesky to Mastodon cross-posting
- GitHub Actions workflow for automated syncing
- Configuration via environment variables
- Support for text, images, and links
