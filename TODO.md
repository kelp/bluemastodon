# BlueMastodon Implementation Plan
(Formerly bluemastodon)

## Scope Clarification
This tool specifically handles synchronizing manual posts from Bluesky to
Mastodon. A separate tool in the blog repository will handle publishing blog
posts to social platforms.

## 1. Project Setup (Day 1)
- [x] Define architecture and coding standards
- [x] Initialize project structure
- [x] Set up virtual environment
- [x] Configure pyproject.toml with dependencies
- [x] Add .gitignore
- [x] Configure pre-commit hooks
- [x] Set up basic GitHub Actions workflow

## 2. API Research (Day 1-2)
- [x] Research Bluesky API authentication and endpoints
- [x] Research Mastodon API authentication and endpoints
- [x] Document required API credentials and how to obtain them
- [x] Plan data models for posts and interaction mapping

## 3. Core Implementation (Day 2-4)
- [x] Implement config.py for loading secrets and settings
- [x] Implement models.py with data classes for posts
- [x] Implement bluesky.py client
  - [x] Authentication
  - [x] Fetching recent posts
  - [x] Handling post content and media
- [x] Implement mastodon.py client
  - [x] Authentication
  - [x] Creating posts
  - [x] Handling media uploads
- [x] Implement sync.py for orchestration
  - [x] Post mapping logic
  - [x] Cross-posting workflow
  - [x] State tracking to avoid duplicates

## 4. Testing (Day 4-5)
- [x] Write unit tests for each module
- [x] Set up mock API responses
- [x] Create integration tests
- [x] Ensure 100% test coverage
- [x] Add test for edge cases (rate limits, API errors, etc.)

## 5. GitHub Actions Setup (Day 6)
- [x] Create workflow for running tests and linters
- [x] Set up scheduled job for cross-posting
- [x] Configure secrets management
- [x] Add manual trigger option
- [x] Test the complete workflow

## 6. Documentation and Finalization (Day 7)
- [x] Complete docstrings for all modules and functions
- [x] Generate and review pydoc documentation
- [x] Write comprehensive README with setup and usage instructions
- [x] Add examples and troubleshooting guide
- [x] Final code review and quality check

## 7. Cleanup and Bug Fixes
- [x] Fix the pre-commit hooks
- [x] Fix bug in Mastodon post handling that caused 'str' cannot be interpreted as int error
- [x] Fix synced post format and link
    - Fixed regex patterns to avoid creating duplicated "https://" prefixes
    - Implemented URL expansion to fix truncated URLs by using the links data from Bluesky
- [x] Fix state file management to prevent double posts
    - Added immediate state saving after successful Mastodon posts
    - Added detection for partial success scenarios
    - Added sync_state.json to .gitignore to prevent committing state
- [x] Improve GitHub Actions cache handling
    - Added unique cache keys with restore-key fallbacks
    - Added workflow concurrency control to prevent race conditions
- [x] Enhance release process in Makefile
    - Added version consistency checks
    - Added CHANGELOG verification
    - Added comprehensive bump-version target
- [x] Change the name of the Test workflow to something more descriptive
  - Renamed sync.yml to bluemastodon.yml with name "BlueMastodon"
  - Renamed test.yml to python-tests.yml with name "Python Tests"
  - Added new security-scan.yml workflow for dependency vulnerability scanning
- [x] Initial update of Makefile to work with run.sh like webdown
- [x] Compare and merge additional Makefile targets and features from webdown
- [x] Setup publishing to pypi, copy what we can from webdown
  - This is the first priority for distribution as it's the most universal method
  - Ensure proper entry points and CLI functionality
  - Update instructions in README when complete
  - Added python-release.yml workflow for automated PyPI publishing
  - Renamed package to "bluemastodon" to avoid naming conflicts on PyPI
  - Fully refactored package and repository to use the new name
- [x] Add documentation on managing GitHub Actions cache
- [ ] Setup GitHub Pages documentation site
- [ ] Decide whether to implement mkdocs documentation system from webdown or simplify webdown's docs to match bluemastodon's approach
- [ ] Consider adding a Homebrew formula after PyPI publishing is complete
  - Lower priority than PyPI but useful for macOS users
  - Could reuse pattern from webdown formula in homebrew-tools tap
  - Should reference the PyPI package rather than installing from source

## 8. Future Enhancements
- [ ] Add support for images and other media types
- [ ] Implement bi-directional sync
- [ ] Add support for replies and interactions
- [ ] Consider support for other platforms (Twitter, etc.)
- [ ] Add deduplication mechanism to avoid duplicate posts if blog publisher also posts to both platforms
