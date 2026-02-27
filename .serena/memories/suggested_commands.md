# Suggested Commands for ani-tupi

## Project Setup
```bash
uv sync                          # Install/sync all dependencies
```

## Running the Application
```bash
uv run ani-tupi                  # Run anime CLI
uv run manga_tupi                # Run manga CLI
uv run main.py --debug           # Run with debug logging
```

## Testing
```bash
uv run pytest                    # Run all tests (711 tests)
uv run pytest tests/ -v          # Verbose output
uv run pytest tests/ -x          # Stop on first failure
uv run pytest -k "test_name"     # Run specific test
uv run pytest --cov=. --cov-report=html  # Coverage report (generates htmlcov/)
uv run pytest -m unit            # Run only unit tests
uv run pytest -m integration     # Run only integration tests
```

## Code Quality
```bash
uv run ruff check .              # Lint the codebase
uv run ruff format .             # Format code (auto-fix)
uv run mypy .                    # Type checking (optional)
uv run pyright .                 # Type checking (optional)
```

## Dependency Management
```bash
uv add package-name              # Add a new dependency
uv remove package-name           # Remove a dependency
uv sync --upgrade                # Update all dependencies
uv pip freeze                    # List installed packages
uv pip show package-name         # Show package info
```

## Building
```bash
uv build                         # Build wheel and sdist (if configured)
```

## Virtual Environment
```bash
# If venv is corrupted/stale (pytest not found):
rm -rf .venv
uv sync

# Direct venv access (bypass uv run):
.venv/bin/python -m pytest       # Run pytest directly
source .venv/bin/activate        # Activate venv in shell
```

## Development Workflow
```bash
# Before committing:
uv run ruff check .              # Check linting
uv run ruff format .             # Format code
uv run pytest                    # Run all tests
```

## Notes
- Use `uv run` for ALL script/CLI execution (NOT poetry, NOT pip)
- Virtual environment is at `.venv/`
- Config file: `pyproject.toml` (don't edit directly, use `uv add/remove`)
- Environment variables stored in `.env` (example in `.env.example`)
- For isolated scripts: `uv run --with package1 --with package2 script.py`
