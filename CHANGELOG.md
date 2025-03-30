# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.9.3] - 2025-03-30

### Changed
- Renamed project from social-sync to bluemastodon to avoid name conflicts on PyPI
- Fixed code formatting and linting issues across the codebase
- Updated project configuration files to use correct module paths
- Updated dependencies to latest versions

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
