# M001: Debug Logging Infrastructure

**Vision:** Replace all print() statements with structured loguru logging and wire the --debug flag to produce complete JSON execution traces, enabling AI agents to analyze app behavior offline.

## Success Criteria

- All 2400+ print() statements replaced with loguru logger calls (verified by grep)
- `--debug` flag activates DEBUG-level logging; without it, console stays clean
- Debug logs write to JSON file at `~/.local/state/ani-tupi/debug.log` with automatic rotation
- Sensitive data (tokens, passwords, auth headers, API keys) is redacted in logs
- End-to-end flow (search → scrape → results) produces complete trace in debug.log
- Log file is valid JSON lines; each line parseable by agents
- UI output (prompts, menus, final results) unchanged — only business logic logs

## Key Risks / Unknowns

- **2400+ print() statements** — Bulk replacement is mechanical but must be systematic to avoid stubs or missed files
- **UI vs debug info boundary** — Must preserve user-facing output while logging execution details
- **Sensitive data detection** — Masking patterns must catch all credential types without false positives

## Proof Strategy

- R001 (debug flag) → retire in S01 by proving JSON logging activates when --debug is set
- R002 (masking) → retire in S01 by unit tests showing tokens/passwords are redacted
- R003 (persistence) → retire in S01 by proving debug.log exists and rotates correctly
- R004 (print replacement) → retire in S02 by grep verification of no remaining print() in business logic
- R005 (full trace) → retire in S03 by end-to-end test showing function calls, variables, HTTP bodies in log

## Verification Classes

- **Contract:** Unit tests for logging config, masking patterns, file rotation
- **Integration:** End-to-end flow with --debug produces readable JSON log with full execution trace
- **Operational:** Log rotation works under repeated runs; file size stays bounded
- **Human verification:** Agent can read debug.log and understand app behavior without reading source code

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 2400+ print() statements replaced with loguru logger calls (verified by grep for "print(" returning 0 results in business logic)
- `--debug` flag wires to logging config; activates DEBUG level, absence keeps console clean
- Debug logs write to JSON file at `~/.local/state/ani-tupi/debug.log` with rotation (latest file always current)
- Sensitive data (tokens, passwords, auth headers, API keys) actually masked in logs (verified by running with real credentials)
- End-to-end flow (search → scrape → results) produces complete trace in debug.log showing every major decision and operation
- Log is valid JSON lines; each line is independently parseable
- All success criteria verified by integration test + human review of debug.log from real flow

## Requirement Coverage

- Covers: R001, R002, R003, R004, R005
- Partially covers: none
- Leaves for later: none
- Orphan risks: none

## Slices

- [x] **S01: Logging Infrastructure Setup** `risk:low` `depends:[]`
  > After this: `--debug` flag routes to loguru; JSON format configured with rotation; debug.log exists at correct path; sensitive data masking tested and working; no integration yet

- [x] **S02: Print Statement Replacement** `risk:medium` `depends:[S01]`
  > After this: All 2400+ print() calls replaced with loguru logger calls; grep confirms no remaining print() in business logic; UI output preserved unchanged

- [x] **S03: Integration & Verification** `risk:low` `depends:[S02]`
  > After this: End-to-end anime search produces complete debug trace in JSON; agent can read log and understand full app behavior; rotation works; all success criteria verified

## Boundary Map

### S01 → S02

**Produces:**
- `utils/logging.py` — Extended `configure_logging(debug: bool)` that:
  - Sets up JSON format with rotation (50MB per file, keep latest)
  - Writes to `~/.local/state/ani-tupi/debug.log`
  - Applies sensitive data masking to all output
  - Returns a configured logger instance
- `mask_sensitive_data(message: str) -> str` — Function that redacts:
  - API tokens (sk-*, Bearer *, etc.)
  - Passwords (password=***, pwd=***, etc.)
  - Auth headers (Authorization: ***, X-API-Key: ***, etc.)
  - Cookie values (sessionid=***, token=***, etc.)
- `get_logger(name: str)` — Returns loguru logger bound to module name

**Consumes:**
- nothing (first slice)

### S02 → S03

**Produces:**
- All internal print() calls replaced with `from loguru import logger; logger.debug(...)`
- Every service, scraper, command, and utility logs:
  - Function entry/exit (name, input variables)
  - Decision points (which branch taken, why)
  - I/O operations (file read/write, network calls, cache operations)
  - API calls (URL, request body, response status, response body)
  - Exceptions (full traceback with context)
- No remaining print() in business logic (verified by grep)
- UI output (prompts, menus, results) still uses print() unchanged

**Consumes from S01:**
- `configure_logging(debug: bool)` initialization in main.py
- `get_logger(name)` to get logger instance per module
- Automatic masking applied by loguru config
