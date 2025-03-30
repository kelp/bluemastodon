# Complete BlueMastodon Renaming Checklist

This document provides a detailed checklist to complete the renaming from `social-sync` to `bluemastodon`.

## Package Directory Structure

- [x] Create `src/bluemastodon/` directory
- [x] Copy all core files from `src/social_sync/` to `src/bluemastodon/`
- [x] Update imports within the new bluemastodon package
- [x] Update docstrings in the bluemastodon package
- [ ] Update the tests to work with the new package name
- [ ] Remove the old `src/social_sync/` directory once tests pass

## Configuration Files

- [x] Update `setup.py` with new package name
- [x] Update `pyproject.toml` with new package name
- [x] Update entry points to reference bluemastodon
- [x] Update environment variable references from `SOCIAL_SYNC_*` to `BLUEMASTODON_*`

## GitHub Workflows

- [x] Update references in `.github/workflows/*.yml` files
- [x] References to `social_sync` module in python invocations
- [ ] Create new GitHub repository named "bluemastodon"
- [ ] Update badges and status URLs in README.md

## Documentation

- [x] Update package description in README.md
- [x] Update GitHub URLs in README.md 
- [x] Add note about former name in README.md
- [x] Update command examples in README.md
- [x] Update TODO.md
- [ ] Update docs/ directory files to reference the new name

## Tests

- [ ] Update imports in all test files
- [ ] Update references to `social_sync` to `bluemastodon`
- [ ] Update test fixtures if needed
- [ ] Ensure coverage report includes only the new package

## Manual Testing

- [ ] Verify installation from source
- [ ] Test command line functionality  
- [ ] Test GitHub workflow triggers
- [ ] Test environment variable handling

## Repository 

- [ ] Create new GitHub repository "bluemastodon"
- [ ] Update local git remote
```bash
git remote set-url origin https://github.com/kelp/bluemastodon.git
```
- [ ] Push changes to the new repository
- [ ] Setup GitHub Pages and other services as needed

## Final Steps

- [ ] Test PyPI release workflow with the renamed package
- [ ] Update any external references or documentation
- [ ] Announce the name change to users

## Command to Find Remaining References

```bash
grep -r "social[_-]sync" --include="*.py" --include="*.md" --include="*.yml" .
```