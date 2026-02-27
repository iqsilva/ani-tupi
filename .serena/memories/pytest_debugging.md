# Pytest Debugging Guide

## Issue: "Failed to spawn: pytest" with uv run

### Symptoms
```bash
$ uv run pytest --version
error: Failed to spawn: `pytest`
  Caused by: No such file or directory (os error 2)
```

### Root Cause
Virtual environment is stale, corrupted, or missing dependencies. This can happen when:
- Virtual environment is deleted but uv state isn't cleared
- uv.lock is updated but venv not rebuilt
- Python version mismatch (3.14 system vs 3.12 venv)

### Solution
```bash
rm -rf .venv
uv sync
uv run pytest --version    # Should now work
```

### Workaround (if venv issues persist)
Run pytest directly from venv:
```bash
.venv/bin/python -m pytest              # Works when uv run fails
.venv/bin/python -m pytest -v           # Verbose
.venv/bin/python -m pytest --cov        # With coverage
```

### Verification
After fixing:
```bash
uv run pytest tests/ -q     # Should pass all 711 tests
```

## Pytest Configuration
- **File**: `pytest.ini`
- **Test Discovery**: `test_*.py` files, `Test*` classes, `test_*` functions
- **Markers**: unit, integration, e2e, slow, requires_selenium, requires_http
- **Coverage Target**: 80%+ on services

## Running Tests
```bash
uv run pytest                           # All tests
uv run pytest tests/ -v                 # Verbose
uv run pytest tests/unit/               # Unit tests only
uv run pytest tests/integration/        # Integration tests only
uv run pytest -m unit                   # By marker
uv run pytest -k test_search            # By name pattern
uv run pytest --cov=. --cov-report=html # Coverage report
uv run pytest -x                        # Stop on first failure
uv run pytest -vv --tb=long             # Very verbose with long traceback
```

## Common Test Failures
1. **Import Errors**: Check if dependencies are in pyproject.toml dev group
2. **Async Tests**: Ensure `pytest-asyncio` is installed (it is)
3. **Missing Fixtures**: Check conftest.py or test file for fixture definitions
4. **Port Conflicts**: Some tests may require specific ports to be available

## Test Files Organization
```
tests/
├── integration/          # Multi-component interactions
├── unit/                 # Isolated service tests
│   ├── commands/
│   ├── services/
│   └── ui/
└── test_*.py             # Root-level integration/unit mix
```

## Performance
- Full test suite: ~17-20 seconds (711 tests)
- Use `-k` flag to run specific tests during development
- Use `-x` to stop on first failure (faster iteration)
