# Changelog

All notable changes to the `ai-sdlc` project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2025-01-03

### 🚀 Major Features

- **8-step workflow**: Added new `07-tasks-plus` step for comprehensive task list review and handoff preparation
  - Inserted between existing `06-tasks` and `07-tests` (now `08-tests`)
  - Ensures implementation-ready documentation with complete context
  - Includes verification criteria for self-contained documentation
- **Tool-agnostic architecture**: Removed all Cursor-specific references and made AI-SDLC work with any AI tool
  - Updated all documentation, code, and configuration files
  - Supports any AI chat interface (Cursor, Claude, ChatGPT, VS Code with AI extensions, etc.)
  - Flexible usage: full CLI workflow OR prompts-only approach

### 📖 Documentation & UX Improvements

- **Enhanced README**: Complete restructure with professional appearance
  - Added badges for PyPI, license, Python version, and AI-powered status
  - Removed GIF placeholder and improved visual hierarchy
  - Added comprehensive table of contents with emoji icons and logical grouping
  - Enhanced "What is AI-SDLC?" section with key features and benefits
  - Improved Quick Start with numbered steps and clear instructions
  - Added workflow modes table and flexible usage options
- **Updated Mermaid diagrams**: Show iteration loops and agent modes
  - Steps 1-5: Connected to "💬 Iterate with AI Chat" node
  - Steps 7-8: Connected to "🤖 Use AI Agent Mode" node
  - Visual representation of different interaction patterns

### 🛠️ Developer Experience

- **Flexible usage options**:
  - **Option 1**: Full CLI workflow with `aisdlc` commands
  - **Option 2**: Prompts-only approach using templates directly with any AI chat
  - Clear instructions for both approaches
- **Simplified contributing**: Removed CLA requirement from contributing guidelines
- **Enhanced error messages**: Made all error messages tool-agnostic
- **Updated configuration**: All `.aisdlc` files include new workflow diagrams

### 🔧 Technical Changes

- Updated all prompt file references to include new `07-tasks-plus-prompt.md`
- Renamed `07-tests.md` to `08-tests-prompt.md` throughout codebase
- Updated step count references from 7 to 8 steps
- Modified `ai_sdlc/commands/init.py` to include new prompt file
- Updated integration tests to handle 8-step workflow
- Changed timeout variable names and messages to be tool-agnostic

### 📦 Backward Compatibility

- **Fully backward compatible**: Existing projects continue to work
- **Automatic migration**: System dynamically reads step configuration
- **No breaking changes**: All existing commands and workflows preserved

### Upgrading

To upgrade to version 0.4.0, use:

```bash
uv pip install --upgrade ai-sdlc
```

No configuration changes are needed - all improvements are backward compatible with existing AI-SDLC projects.

## [0.3.0] - 2025-01-15

### Overview

Version 0.3.0 brings significant improvements to error handling, security, and overall robustness of the tool. This release also introduces a comprehensive testing framework to ensure stability as the project evolves.

### Added

- **Comprehensive testing framework with pytest**
  - Basic test structure with fixtures and helpers
  - Unit tests for utility functions and commands
  - Integration tests for the CLI workflow
- **Enhanced error handling and robustness**
  - Detailed error messages for AI agent failures including stdout/stderr
  - Timeout handling for AI agent calls (45 second default)
  - Comprehensive file I/O error handling in all commands
  - Lock file corruption handling (gracefully handles invalid JSON)
  - Config file corruption handling (shows helpful error for invalid TOML)
- **Enhanced `aisdlc init` command**
  - Now scaffolds a default `.aisdlc` configuration file into the new project
  - Automatically creates a `prompts/` directory populated with default prompt templates for all SDLC steps
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

- An AI agent command (like `cursor agent`) must be available in your PATH for the `next` command to work correctly
- AI-SDLC continues to require Python 3.13 or newer

## [0.2.0] - 2025-05-17

- Python 3.13 support
- UV-first installation
- Streamlined lifecycle (removed release planning/retro steps)

## [0.1.0] - Initial Release

- Initial version with basic SDLC workflow
- Support for the initial lifecycle
- Integration with AI agents
