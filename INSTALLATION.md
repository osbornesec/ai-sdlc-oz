# AI-SDLC Installation and Testing Guide

## Prerequisites

- Python 3.8 or higher
- Git
- uv package manager (recommended) or pip

## Installation

### Option 1: Using uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-sdlc-oz.git
cd ai-sdlc-oz

# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the package in development mode
uv pip install -e .
```

### Option 2: Using pip

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-sdlc-oz.git
cd ai-sdlc-oz

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package in development mode
pip install -e .
```

## Configuration

### Required: Anthropic API Key

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

> **Note:** Context7 integration works automatically without any API key. It will detect libraries in your project and enrich AI prompts with relevant documentation.

## Testing the Installation

### 1. Verify Installation

```bash
aisdlc --help
```

### 2. Initialize a Test Project

```bash
# Create a test directory
mkdir test-project
cd test-project

# Initialize AI-SDLC
aisdlc init
```

### 3. Create a New Feature

```bash
# Start a new feature
aisdlc new "Add user authentication with JWT tokens"

# Check status
aisdlc status

# See detected libraries and context
aisdlc context
```

### 4. Progress Through Workflow

```bash
# Get next task
aisdlc next

# Continue through all 8 steps:
# 00-idea → 01-prd → 02-prd-plus → 03-system-template
# → 04-systems-patterns → 05-tasks → 06-tasks-plus → 07-tests

# Complete the feature
aisdlc done
```

## Example Workflow

```bash
# 1. Initialize project
$ aisdlc init
AI-SDLC initialized successfully!

# 2. Start new feature
$ aisdlc new "Implement REST API for user management"
Feature created: implement-rest-api-for-user-management

# 3. Check context (with Context7 integration)
$ aisdlc context
Detected Libraries:
- FastAPI (Python web framework)
- SQLAlchemy (Python ORM)
- Pydantic (Data validation)

# 4. Work through steps
$ aisdlc next
Current step: 00-idea
Generated: .aisdlc/features/implement-rest-api/00-idea.md

$ aisdlc next
Current step: 01-prd
Generated: .aisdlc/features/implement-rest-api/01-prd.md
# ... continue through all steps

# 5. Complete feature
$ aisdlc done
Feature archived to: .aisdlc/archive/implement-rest-api/
```

## Troubleshooting

### Command not found

If `aisdlc` command is not found:

```bash
# Check if package is installed
pip show ai-sdlc

# Ensure pip scripts are in PATH
export PATH="$PATH:~/.local/bin"
```

### Missing API Key

```bash
# Check if API key is set
echo $ANTHROPIC_API_KEY

# Set it if missing
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Context7 Not Working

```bash
# Verify Context7 is detecting libraries
aisdlc context --verbose

# Context7 works without an API key
# Check if it's properly detecting your libraries
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ai_sdlc

# Run specific test files
pytest tests/unit/test_context7_service.py
pytest tests/integration/test_cli_flow.py
```

## Development

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Run linting
ruff check .

# Run type checking
mypy ai_sdlc

# Format code
ruff format .
```