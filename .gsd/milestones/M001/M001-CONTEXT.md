# M001: Debug Logging Infrastructure

**Gathered:** 2026-03-15
**Status:** Ready for planning

## Project Description

ani-tupi is a Brazilian Portuguese CLI for anime and manga with multi-source support, AniList integration, and external player support. Currently uses 2400+ print() statements scattered across 449 files, with logging infrastructure partially set up but not integrated.

## Why This Milestone

The codebase has no visibility into execution for AI agents troubleshooting issues. Replacing print() with structured logging and wiring the `--debug` flag enables complete execution traces that agents can analyze offline without reading source code.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Run `ani-tupi --debug` and see debug logs written to `~/.local/state/ani-tupi/debug.log` as JSON
- Share debug.log with an AI agent for offline analysis
- Review complete execution traces showing every function call, variable, and HTTP interaction
- Know that sensitive data (tokens, auth headers, passwords) is automatically masked in logs

### Entry point / environment

- Entry point: `ani-tupi --debug` CLI flag
- Environment: local dev / production (any environment)
- Live dependencies involved: none (logging is local)

## Completion Class

- **Contract complete:** All internal print() calls replaced, logging config wired to --debug flag
- **Integration complete:** End-to-end flow (search → scrape → download → watch) produces readable debug trace
- **Operational complete:** Debug log rotates correctly, latest file accessible, sensitive data actually masked

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Running `ani-tupi --debug --query "jujutsu kaisen"` produces `debug.log` with full trace (search, API calls, scraper execution, caching decisions)
- Sensitive data (tokens, API keys, passwords) is redacted in the log, not visible
- Log file is valid JSON lines, parseable by agents
- Without `--debug`, console output unchanged (UI still works normally)

## Risks and Unknowns

- **2400+ print() statements across 449 files** — bulk replacement is mechanical but needs systematic approach to avoid missing files or creating stubs
- **Determining what counts as "debug info" vs "UI output"** — must preserve user-facing prompts/menus while logging everything else
- **Sensitive data detection** — masking patterns must catch all credential types without false positives

## Existing Codebase / Prior Art

- `utils/logging.py` — loguru setup exists but not fully integrated; uses stdlib logging fallback in many services
- `main.py` — `--debug` flag already defined but not wired to logging
- `models/config.py` — Pydantic config system; logging not yet integrated here
- `services/` — Mix of stdlib `logging.getLogger()` and `print()` calls; one service (`local_manga_service.py`) already uses loguru

## Relevant Requirements

- R001: Debug Flag Enables Full Execution Tracing
- R002: Sensitive Data Masking
- R003: Debug Log Persistence and Rotation
- R004: Print Statements Replaced with Loguru Logger
- R005: Full Execution Trace Completeness

## Scope

### In Scope

- Extend `utils/logging.py` to add JSON format, debug.log file output, sensitive data masking, --debug wiring
- Systematically replace print() calls with loguru logger calls in all 449 files
- Ensure debug logs capture full execution (function calls, variables, HTTP bodies, caching decisions)
- Test that sensitive data is actually masked in logs
- Verify end-to-end flow produces readable, complete debug trace

### Out of Scope / Non-Goals

- Structured logging for production metrics (this is for debugging, not observability)
- Real-time log streaming or agent connection (logs are files for offline analysis)
- Performance optimization of logging (correctness first)
- Log sampling or filtering (capture everything in debug mode)

## Technical Constraints

- Must not break existing UI output (prompts, menus, final results stay as-is)
- Sensitive data masking must be bulletproof (err on side of over-masking)
- JSON format must be line-delimited for easy parsing
- Logging must not significantly slow down the app

## Integration Points

- `main.py` — Wire --debug flag to logging config
- All service layers — Replace print() with logger calls
- All scrapers/plugins — Log their execution
- All UI components — Log decisions, not output
- Config system — May need to track debug mode state

## Open Questions

- Should debug logs include the full JSON response body from scraper APIs, or just key fields? → **Decision: full body, masked for sensitive fields**
- Should function entry/exit be logged for every function, or just "interesting" ones? → **Decision: every function that does I/O, API calls, or makes decisions**
- How to handle libraries (like requests, aiohttp) that do their own logging? → **Decision: intercept at our call sites, don't try to reconfigure dependencies**
