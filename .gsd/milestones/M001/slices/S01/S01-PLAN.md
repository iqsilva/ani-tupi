# S01: Logging Infrastructure Setup

**Goal:** Set up loguru logging to produce JSON-formatted debug logs with automatic rotation, sensitive data masking, and wire the `--debug` flag to control activation.

**Demo:** Running `ani-tupi --debug --query test` produces `~/.local/state/ani-tupi/debug.log` as valid JSON lines with no visible credentials.

## Must-Haves

### Truths

- `--debug` flag is passed to logging config and activates DEBUG level
- Without `--debug`, console output stays clean (no debug info leaks)
- Debug logs write to `~/.local/state/ani-tupi/debug.log` in JSON format
- Log file rotates when it reaches 50MB; latest file is always current
- All instances of API tokens, passwords, auth headers, and cookie values are masked (not visible in logs)
- Each log line is valid JSON and independently parseable

### Artifacts

- `utils/logging.py` — Extended with JSON format, debug.log output, rotation, masking (min 100 lines)
  - Exports: `configure_logging(debug: bool)`, `get_logger(name: str)`, `mask_sensitive_data(message: str)`
  - Actual implementation, not stubs
- Unit tests in `tests/test_logging_config.py` — verify masking patterns, file rotation, JSON format (min 30 lines)
  - Test: tokens are masked (Bearer, sk-, etc.)
  - Test: passwords are masked (password=, pwd=, etc.)
  - Test: auth headers are masked (Authorization, X-API-Key, etc.)
  - Test: JSON format is valid
  - Test: rotation happens at 50MB
- `main.py` — Updated to call `configure_logging(args.debug)` at startup

### Key Links

- `main.py` → `utils/logging.py` via import of `configure_logging`
- `utils/logging.py` → loguru (already in deps)
- Tests → `utils/logging.py` via import of `configure_logging`, `mask_sensitive_data`, `get_logger`

## Tasks

- [x] **T01: Extend logging.py with JSON format, rotation, and masking**
  Setup loguru to output JSON to debug.log with rotation, implement sensitive data masking patterns. ✅ DONE

- [x] **T02: Wire --debug flag to logging in main.py**
  Call configure_logging(args.debug) at startup so flag activates logging. ✅ DONE

- [ ] **T03: Write unit tests for logging config and masking**
  Verify JSON format, rotation, and all credential types are masked.

## Files Likely Touched

- `utils/logging.py`
- `main.py`
- `tests/test_logging_config.py` (new)
- `tests/conftest.py` (if needed for temp file fixtures)
