# AI-SDLC Release Notes - v0.3.0

## Overview

Version 0.3.0 of AI-SDLC brings significant improvements to error handling, security, and overall robustness of the tool. This release also introduces a comprehensive testing framework to ensure stability as the project evolves.

## Key Improvements

### Enhanced Error Handling and Robustness

- **Improved Cursor Agent Error Handling**: You now get detailed error messages when Cursor agent calls fail, including stdout and stderr output for better debugging.
- **Timeout Protection**: A 5-minute timeout has been added to Cursor agent calls to prevent indefinite hangs.
- **Comprehensive File I/O Error Handling**: All file operations now have proper exception handling with informative error messages.
- **Configuration File Validation**: The tool now gracefully handles corrupted TOML configuration files with clear error messages.
- **Lock File Protection**: Corrupted JSON in the lock file is now handled gracefully, treating it as empty with a warning.

### Secure Temporary File Management

- **Secure Temporary Files**: Replaced hardcoded `/tmp/aisdlc_prompt.md` with the secure `tempfile.NamedTemporaryFile` mechanism.
- **Automatic File Cleanup**: Added proper cleanup in `finally` blocks to prevent leaking sensitive prompt data.

### Improved Project Navigation

- **Robust Project Root Detection**: You can now run `aisdlc` commands from any subdirectory within your project.
- **Upward Directory Search**: The tool automatically searches parent directories to find the project root (marked by the `.aisdlc` file).

### Enhanced User Experience

- **Verbose Output**: The `next` command now provides detailed progress information at each step.
- **Clear Error Messages**: All error messages have been improved to be more informative and actionable.

### Testing Infrastructure

- **Comprehensive Test Suite**: Added a full testing framework using pytest.
- **Unit Tests**: Core utility functions and command modules now have dedicated unit tests.
- **Integration Tests**: End-to-end workflow tests ensure commands work together correctly.
- **Test Fixtures**: Reusable fixtures for mocking and temporary project environments.

## Developer Improvements

- **Development Dependencies**: Added pytest, pytest-mock, ruff, and pyright to the dev dependencies.
- **Documentation Updates**: Improved documentation for development setup and testing.

## Upgrading

To upgrade to version 0.3.0, use:

```bash
uv pip install --upgrade ai-sdlc
```

No configuration changes are needed - all improvements are backward compatible with existing AI-SDLC projects.

## Known Issues

- The `cursor agent` command must still be available in your PATH for the `next` command to work correctly.
- AI-SDLC continues to require Python 3.13 or newer.

## Future Directions

We're exploring:
- Multiple AI model provider support beyond Cursor
- Context window management for larger projects
- Extended lifecycle steps for deployment and infrastructure
- See the Roadmap section in README.md for more planned improvements

---

Thank you to all contributors who helped make this release possible!