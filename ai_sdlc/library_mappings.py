"""Library mappings and patterns for Context7 integration."""

import re

# Compiled regex patterns for library detection
LIBRARY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'using\s+(\w+)', re.IGNORECASE),
    re.compile(r'built\s+with\s+(\w+)', re.IGNORECASE),
    re.compile(r'based\s+on\s+(\w+)', re.IGNORECASE),
    re.compile(r'framework[:\s]+(\w+)', re.IGNORECASE),
    re.compile(r'library[:\s]+(\w+)', re.IGNORECASE),
    re.compile(r'database[:\s]+(\w+)', re.IGNORECASE),
    re.compile(r'leveraging\s+(\w+)', re.IGNORECASE),
]

# Common library name mappings to help with resolution
LIBRARY_MAPPINGS: dict[str, str] = {
    # Frontend
    "react": "react",
    "reactjs": "react",
    "vue": "vue",
    "vuejs": "vue",
    "angular": "angular",
    "svelte": "svelte",
    "next": "nextjs",
    "nextjs": "nextjs",
    "next.js": "nextjs",

    # Backend
    "express": "express",
    "expressjs": "express",
    "fastapi": "fastapi",
    "django": "django",
    "flask": "flask",
    "rails": "rails",
    "ruby on rails": "rails",

    # Databases
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "mysql": "mysql",
    "mongodb": "mongodb",
    "mongo": "mongodb",
    "redis": "redis",

    # Testing
    "jest": "jest",
    "pytest": "pytest",
    "mocha": "mocha",
    "vitest": "vitest",
    "cypress": "cypress",

    # State Management
    "redux": "redux",
    "mobx": "mobx",
    "zustand": "zustand",
    "pinia": "pinia",

    # Build Tools
    "webpack": "webpack",
    "vite": "vite",
    "rollup": "rollup",
    "parcel": "parcel",

    # ORMs
    "prisma": "prisma",
    "sqlalchemy": "sqlalchemy",
    "typeorm": "typeorm",
    "sequelize": "sequelize",
}
