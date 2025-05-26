# Changelog

All notable changes to the `ai-sdlc` project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-01-15

### Overview
Version 0.3.0 brings significant improvements to error handling, security, and overall robustness of the tool. This release also introduces a comprehensive testing framework to ensure stability as the project evolves.

### Added
- **Comprehensive testing framework with pytest**
  - Basic test structure with fixtures and helpers
  - Unit tests for utility functions and commands
  - Integration tests for the CLI workflow
- **Enhanced error handling and robustness**
  - Detailed error messages for Cursor agent failures including stdout/stderr
  - Timeout handling for Cursor agent calls (5 minute default)
  - Comprehensive file I/O error handling in all commands
  - Lock file corruption handling (gracefully handles invalid JSON)
  - Config file corruption handling (shows helpful error for invalid TOML)
- **Enhanced `aisdlc init` command**
  - Now scaffolds a default `.aisdlc` configuration file into the new project
  - Automatically creates a `prompts/` directory populated with default prompt templates for all 7 SDLC steps
  - Displays a comprehensive and styled welcome message upon initialization, including:
    - An ASCII art logo for "AI-SDLC"
    - A brief explanation of how AI-SDLC works
    - A guide on understanding the compact status bar shown after commands
    - Quick "Getting Started" instructions for the main workflow (`new`, `next`, `done`)
- **Packaged default configuration and templates**
  - Default `.aisdlc` configuration and all prompt templates within the `ai-sdlc` distribution
  - Ensures `init` can robustly scaffold new projects

### Changed
- **Improved temporary file handling in `next` command**
  - Replaced hardcoded `/tmp/aisdlc_prompt.md` with secure `tempfile.NamedTemporaryFile`
  - Added proper cleanup in `finally` block to prevent leaks
- **Enhanced `next` command with verbose output**
  - Added informative messages about reading files, creating temporary files
  - Shows progress indicators at each step
- **Improved project root detection**
  - New `find_project_root()` function that searches upward for `.aisdlc` file
  - Allows running commands from subdirectories of the project

### Security
- **Secure temporary file management**
  - Implemented secure temporary file handling with proper permissions
  - Automatic file cleanup to prevent leaking sensitive prompt data

### Developer Improvements
- Added pytest, pytest-mock, ruff, and pyright to dev dependencies
- Improved documentation for development setup and testing

### Upgrading
To upgrade to version 0.3.0, use:
```bash
uv pip install --upgrade ai-sdlc
```
No configuration changes are needed - all improvements are backward compatible with existing AI-SDLC projects.

### Known Issues
- The `cursor agent` command must still be available in your PATH for the `next` command to work correctly
- AI-SDLC continues to require Python 3.13 or newer

## [0.2.0] - 2025-05-17

- Python 3.13 support
- UV-first installation
- Streamlined 7-step lifecycle (removed release planning/retro steps)

## [0.1.0] - Initial Release

- Initial version with basic SDLC workflow
- Support for the 7-step lifecycle
- Integration with Cursor agent
