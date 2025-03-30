# BlueMastodon Renaming Guide

This document outlines the steps needed to complete the renaming from `social-sync` to `bluemastodon`.

## Completed Steps
- Created new package structure in `src/bluemastodon/`
- Updated package imports in the new module files
- Updated main docstrings and entry points
- Updated workflows to reference the new module name
- Updated setup.py with the new package name and GitHub URL
- Updated README.md with the new repository information
- Added a helper script: `scripts/update-to-bluemastodon.sh`

## Remaining Steps

1. **Fix Test Coverage Issues**:
   - Update tests to use the new package name
   - Either create new test files or update the existing ones
   - Fix import path issues and references

2. **Repository Rename Procedure**:
   - Commit all current changes
   - Create a new GitHub repository called "bluemastodon"
   - Update git remote:
     ```bash
     git remote set-url origin https://github.com/kelp/bluemastodon.git
     ```
   - Push changes to the new repository

3. **Update Additional References**:
   - Check for any remaining references to "social_sync" or "social-sync" in the codebase
   - Update any documentation or external references

4. **Test Suite Overhaul**:
   - After the repository rename, update the test suite to work with the new module structure
   - Fix the GitHub Actions workflows if needed

5. **Verify PyPI Release Process**:
   - Test the release workflow on the new repository
   - Ensure proper package name and version detection

## Command to Find Remaining References

```bash
grep -r "social[_-]sync" --include="*.py" --include="*.md" --include="*.yml" .
```

Once the repository has been renamed and all references updated, you can finalize the migration by removing the old `src/social_sync` directory after ensuring all tests pass with the new structure.