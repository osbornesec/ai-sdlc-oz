# Context7 Integration Guide for AI-SDLC

This guide explains how Context7 MCP (Model Context Protocol) has been integrated into AI-SDLC to enhance the AI-assisted software development workflow.

## What is Context7?

Context7 MCP provides real-time access to up-to-date library and framework documentation. It helps AI assistants provide more accurate, current information by fetching documentation directly from authoritative sources.

## How It Works in AI-SDLC

### 1. Automatic Library Detection

When you run `aisdlc next`, the system automatically:
- Scans your previous step content for library/framework mentions
- Resolves library names to Context7 IDs
- Fetches relevant documentation
- Injects it into your prompt

### 2. Manual Library Management

Use the `aisdlc context` command to manage documentation:

```bash
# View detected libraries for current step
aisdlc context

# Force specific libraries
aisdlc context --libraries react,fastapi,postgresql

# Show cached documentation
aisdlc context --show-cache

# Clear documentation cache
aisdlc context --clear-cache
```

### 3. Enhanced Prompts

Your AI prompts now include a `<context7_docs>` section with:
- Current API references
- Best practices and patterns
- Version-specific information
- Framework conventions

## Configuration

Add Context7 settings to your `.aisdlc` file:

```toml
[context7]
enabled = true
default_tokens = 10000

# Auto-fetch libraries for specific steps
[[context7.auto_fetch]]
step = "3-system-template"
libraries = ["react", "fastapi", "django"]

[[context7.auto_fetch]]
step = "7-tests"
libraries = ["pytest", "jest", "vitest"]
```

## Benefits

1. **Accuracy**: AI references actual, current documentation
2. **Best Practices**: Designs align with library conventions
3. **Version Awareness**: Considers specific version capabilities
4. **Reduced Hallucination**: Less guessing about APIs

## Example Workflow

1. Start a new project:
   ```bash
   aisdlc new "Build a React dashboard with FastAPI backend"
   ```

2. Fill out initial steps (0-idea, 1-prd, 2-prd-plus)

3. Check detected libraries before system design:
   ```bash
   aisdlc context
   ```

4. Generate system architecture prompt:
   ```bash
   aisdlc next
   ```

   The prompt now includes React and FastAPI documentation!

5. Continue through remaining steps with enriched prompts

## Supported Libraries

Context7 supports documentation for many popular libraries including:

**Frontend**: React, Vue, Angular, Svelte, Next.js
**Backend**: Express, FastAPI, Django, Flask, Rails
**Databases**: PostgreSQL, MySQL, MongoDB, Redis
**Testing**: Jest, Pytest, Mocha, Vitest, Cypress
**And many more...**

## Technical Details

### Cache Management

Documentation is cached in `.context7_cache/` with:
- 7-day expiry for freshness
- Automatic cleanup of old entries
- Manual clearing via `aisdlc context --clear-cache`

### Library Name Resolution

The system intelligently maps common variations:
- "react" → React documentation
- "nextjs", "next.js", "next" → Next.js documentation
- "postgres", "postgresql" → PostgreSQL documentation

### Integration Points

Context7 enhances these AI-SDLC steps:
- **Step 3**: System architecture with framework docs
- **Step 4**: Design patterns with implementation examples
- **Step 5-6**: Task planning with API references
- **Step 7**: Test generation with testing framework docs

## Troubleshooting

### Libraries Not Detected

If expected libraries aren't detected:
1. Check spelling in your content
2. Use `aisdlc context --libraries lib1,lib2` to force inclusion
3. Ensure libraries are mentioned clearly in previous steps

### Documentation Not Appearing

If Context7 docs aren't in your prompts:
1. Verify Context7 is enabled in `.aisdlc`
2. Check cache with `aisdlc context --show-cache`
3. Try clearing cache: `aisdlc context --clear-cache`

### MCP Connection Issues

If Context7 MCP is unavailable:
- The system gracefully falls back to standard prompts
- You'll see a note about Context7 being unavailable
- Workflow continues normally without documentation

## Future Enhancements

Planned improvements include:
- IDE integration for real-time docs
- Version-specific documentation
- Multi-language support
- Project-wide library tracking
- Integration with package.json/requirements.txt
