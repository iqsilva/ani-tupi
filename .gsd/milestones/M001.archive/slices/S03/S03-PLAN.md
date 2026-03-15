# S03: Integration & Verification

**Goal:** Verify that the logging infrastructure and print() replacements work end-to-end, producing complete and readable debug traces that agents can analyze.

**Demo:** Running `ani-tupi --debug --query "anime name"` produces `debug.log` with full execution trace (search queries, API calls, responses, caching decisions, scraper execution); agent can read log without code.

## Must-Haves

### Truths

- Running `ani-tupi --debug --query "jujutsu kaisen"` produces valid JSON lines in debug.log
- Log contains searchable entries showing: search API call, scraper execution, cache checks, results
- Log rotation works correctly under repeated large searches
- Sensitive data (tokens, API responses with keys) is actually masked, not visible
- Without `--debug` flag, console output is clean and unchanged
- Debug log entries show function names, input variables, decision branches, and outcomes
- All integration tests pass, including end-to-end flows

### Artifacts

- Integration test in `tests/test_debug_logging_e2e.py` (min 50 lines)
  - Test: `ani-tupi --debug --query test` produces debug.log
  - Test: Log file contains valid JSON lines
  - Test: Sensitive data is masked (run with real API keys, verify not in log)
  - Test: Log entries show function calls, variables, decisions
  - Test: Log rotation works at 50MB boundary
- Manual verification report: review of actual debug.log from real flow showing:
  - Search query execution
  - Scraper API calls with masked credentials
  - Cache hit/miss decisions
  - Result processing
  - No visible secrets or sensitive data
- All tests pass: `uv run pytest` returns 0 failures

### Key Links

- Integration test → Services and commands via normal import
- Services/commands → logging via loguru (wired in S01 and S02)

## Tasks

- [ ] **T01: Write integration tests for debug logging**
  Create end-to-end test that exercises full flow with --debug flag and verifies log output.

- [ ] **T02: Manual verification of debug.log output**
  Run actual anime search with --debug, review debug.log for completeness and data masking.

- [ ] **T03: Verify rotation and performance**
  Run large searches to trigger log rotation; verify latest file is current and app performance is acceptable.

- [ ] **T04: Final verification and cleanup**
  Confirm all success criteria met; verify grep shows no print() in business logic; run full test suite.

## Files Likely Touched

- `tests/test_debug_logging_e2e.py` (new)
- `tests/conftest.py` (may need fixtures for temp log directories)
- Possibly `models/config.py` if debug mode needs to be tracked in settings
