# PyPI Publishing Setup

This document explains how to set up automated PyPI publishing for the AI-SDLC project.

## Overview

The project uses GitHub Actions to automatically:
1. Run tests on every push and PR
2. Build and publish to PyPI when a new tag is created
3. Create GitHub releases with changelog notes

## PyPI Trusted Publishing Setup

To enable automatic PyPI publishing, you need to configure PyPI Trusted Publishing:

### 1. Create PyPI Account and Project

1. Go to [PyPI](https://pypi.org) and create an account if you don't have one
2. Create a new project named `ai-sdlc` (or claim it if it doesn't exist)

### 2. Configure Trusted Publishing

1. Go to your project on PyPI: https://pypi.org/manage/project/ai-sdlc/
2. Navigate to "Publishing" tab
3. Add a new "trusted publisher" with these settings:
   - **Owner**: `ParkerRex` (or your GitHub username)
   - **Repository name**: `ai-sdlc`
   - **Workflow name**: `release.yml`
   - **Environment name**: `release`

### 3. Create GitHub Environment

1. Go to your GitHub repository settings
2. Navigate to "Environments"
3. Create a new environment named `release`
4. Add protection rules if desired (e.g., require manual approval)

## How It Works

### Continuous Integration (CI)

The `.github/workflows/ci.yml` workflow runs on every push and PR:

- **Multi-Python Testing**: Tests against Python 3.9, 3.10, 3.11, 3.12, 3.13
- **Code Quality**: Runs ruff linting and formatting checks
- **Type Checking**: Runs mypy for type safety
- **Test Coverage**: Generates coverage reports and uploads to Codecov
- **Security**: Runs bandit and safety checks
- **Integration Tests**: Tests CLI functionality end-to-end

### Release Process

The `.github/workflows/release.yml` workflow runs when you push a tag:

1. **Test**: Runs full test suite
2. **Build**: Creates wheel and source distributions using `uv build`
3. **Publish**: Uploads to PyPI using trusted publishing (no API keys needed!)
4. **Release**: Creates GitHub release with changelog and artifacts

## Creating a Release

To create a new release:

1. **Update version** in `pyproject.toml` and `ai_sdlc/__init__.py`
2. **Update CHANGELOG.md** with new version notes
3. **Commit changes**: `git commit -m "chore: bump version to X.Y.Z"`
4. **Create and push tag**: 
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z: Description"
   git push origin vX.Y.Z
   ```
5. **GitHub Actions will automatically**:
   - Run tests
   - Build packages
   - Publish to PyPI
   - Create GitHub release

## Local Development

Install development dependencies:
```bash
uv sync --all-extras --dev
```

Run tests:
```bash
uv run pytest
```

Run linting:
```bash
uv run ruff check .
uv run ruff format .
```

Build package locally:
```bash
uv build
```

## Security

- **No API keys**: Uses PyPI trusted publishing for secure, keyless publishing
- **Environment protection**: Release environment can have approval requirements
- **Security scanning**: Automated bandit and safety checks
- **Dependency scanning**: GitHub Dependabot enabled

## Troubleshooting

### PyPI Publishing Fails

1. Check that trusted publishing is configured correctly on PyPI
2. Verify the GitHub environment name matches (`release`)
3. Ensure the workflow name matches (`release.yml`)
4. Check that the repository owner/name are correct

### Tests Fail

1. Check the CI logs for specific error messages
2. Run tests locally: `uv run pytest -v`
3. Check code formatting: `uv run ruff check .`
4. Verify type checking: `uv run mypy ai_sdlc`

### Build Fails

1. Check that all files are included in the package
2. Verify hatchling configuration in `pyproject.toml`
3. Test build locally: `uv build`
