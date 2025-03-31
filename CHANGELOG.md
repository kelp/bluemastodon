# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
