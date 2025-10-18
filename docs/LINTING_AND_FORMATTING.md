# Linting & Formatting Commands

## Quick Reference

All commands can be run from the **root directory** of the project.

### ✅ Complete Quality Check (Recommended)

```bash
npm run check
```

This runs:
- ESLint on all web packages (TypeScript/React)
- Ruff on all Python code (apps + libs)
- Black + isort to format Python code

### 🔍 Type Checking

```bash
npm run type-check
```

Runs TypeScript type checking across all web packages:
- `web-shell`
- `web-analysis`
- `ui` package

### 🧹 Linting Only

#### All Code (JS + Python)
```bash
npm run lint
```

#### JavaScript/TypeScript Only
```bash
turbo run lint
```

#### Python Only
```bash
npm run lint:python
```
or directly:
```bash
ruff check apps libs
```

### ✨ Auto-Fix/Format

#### All Code (JS + Python)
```bash
npm run fix
# or
npm run format
```

#### JavaScript/TypeScript Only
```bash
npm run fix:js
```

#### Python Only
```bash
npm run fix:python
```
or directly:
```bash
black apps libs
isort apps libs
ruff check --fix apps libs
```

## Individual Package Commands

### Web Shell (Host)

```bash
cd apps/web-shell

# Type check
npm run type-check

# Lint
npm run lint

# Dev server
npm run dev

# Build
npm run build
```

### Web Analysis (Remote)

```bash
cd apps/web-analysis

# Type check
npm run type-check

# Lint
npm run lint

# Dev server
npm run dev

# Build
npm run build
```

### UI Package

```bash
cd packages/ui

# Type check
npm run type-check

# Lint
npm run lint
```

## What Each Tool Does

### ESLint (JavaScript/TypeScript)
- **Purpose**: Catches code quality issues, enforces best practices
- **Config**: `eslint.config.js` (root and per-package)
- **Rules**: React Hooks, TypeScript, code style
- **Files**: `*.ts`, `*.tsx`

### TypeScript Compiler (tsc)
- **Purpose**: Type checking, ensures type safety
- **Config**: `tsconfig.json` in each package
- **Mode**: `--noEmit` (type check only, no build)
- **Files**: All TypeScript files

### Ruff (Python)
- **Purpose**: Fast Python linter (replaces Flake8, isort, etc.)
- **Config**: `pyproject.toml`
- **Files**: All `.py` files in `apps/` and `libs/`

### Black (Python)
- **Purpose**: Opinionated Python code formatter
- **Config**: `pyproject.toml` (line-length: 100)
- **Files**: All `.py` files in `apps/` and `libs/`

### isort (Python)
- **Purpose**: Sorts Python imports
- **Config**: `pyproject.toml` (Black compatible)
- **Files**: All `.py` files in `apps/` and `libs/`

## CI/CD Integration

For CI/CD pipelines, use these commands:

```bash
# Full check (fails on any issue)
npm run check

# Type checking
npm run type-check

# Linting (no auto-fix)
npm run lint
```

## Pre-commit Setup (Optional)

If you want to run checks before each commit, you can set up a pre-commit hook:

```bash
# .git/hooks/pre-commit
#!/bin/sh
npm run check
```

## Turbo Cache

Turborepo caches task results for faster subsequent runs:

```bash
# Clear cache if needed
npm run clean

# Run with cache
npm run lint   # Fast on subsequent runs

# Force run without cache
turbo run lint --force
```

## VS Code Integration

All linting is configured to work with VS Code:
- **ESLint**: Auto-lint on save (if extension installed)
- **TypeScript**: Real-time type checking in editor
- **Python**: Black/Ruff format on save (if extensions installed)

### Recommended Extensions

- ESLint (`dbaeumer.vscode-eslint`)
- Python (`ms-python.python`)
- Pylance (`ms-python.vscode-pylance`)
- Black Formatter (`ms-python.black-formatter`)

## Current Status ✅

All linting and formatting is passing:

```
✅ TypeScript type checking: PASSED
✅ ESLint (web packages): PASSED
✅ Ruff (Python): PASSED
✅ Black formatting: PASSED
✅ isort imports: PASSED
```

## Troubleshooting

### ESLint Warnings
```bash
# If you see module type warnings, ensure:
# - "type": "module" is in root package.json ✅ (already done)
```

### TypeScript Errors
```bash
# Clear turbo cache and node_modules
npm run clean
rm -rf node_modules
npm install
```

### Python Import Errors
```bash
# Ensure all directories have __init__.py
# (Already done - 146 files created)
```

## Summary

**Simplest workflow:**

```bash
# From project root:
npm run check    # Check everything
npm run fix      # Fix everything
```

That's it! 🎯
