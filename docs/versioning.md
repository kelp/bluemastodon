# Versioning Guidelines for Social-Sync

Social-Sync follows [Semantic Versioning](https://semver.org/) (SemVer) for its
release numbering.

## Version Structure

Versions follow the format `MAJOR.MINOR.PATCH`:

- **MAJOR**: Incremented for incompatible API changes
- **MINOR**: Incremented for backwards-compatible functionality additions
- **PATCH**: Incremented for backwards-compatible bug fixes

## Version Command Usage

The Makefile includes several commands to manage versions:

```bash
# Bump patch version (1.0.0 -> 1.0.1)
make version-patch

# Bump minor version (1.0.0 -> 1.1.0)
make version-minor

# Bump major version (1.0.0 -> 2.0.0)
make version-major

# Set a specific version
make version-set VERSION=1.2.3

# Create a git tag for the current version
make version-tag
```

## Release Workflow

1. Ensure all tests pass: `make test`
2. Update the appropriate version: `make version-patch` (or other version command)
3. Run the release process: `make release`
4. Commit the version change: `git commit -am "Bump version to X.Y.Z"`
5. Create a tag: `make version-tag`
6. Push the tag: `git push origin vX.Y.Z`
7. Publish to PyPI: `make publish`

## Version History

- **0.9.0**: Initial beta release
  - Complete implementation of Bluesky to Mastodon cross-posting
  - Robust duplicate post prevention with two-layer approach
  - Comprehensive test suite with 100% coverage
  - GitHub Actions workflows for CI/CD and scheduled cross-posting
  - Complete documentation
  - Pending bugfixes for production stability

## Future Development

Plans for future versions include:

- Support for more media types
- Bi-directional sync between platforms
- Support for replies and interactions
- Dashboard for monitoring
- Support for additional social platforms
