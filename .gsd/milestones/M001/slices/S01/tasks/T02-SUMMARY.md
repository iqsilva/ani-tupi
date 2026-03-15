---
id: T02
parent: S01
milestone: M001
provides:
  - --debug flag wired to logging configuration
  - configure_logging() called at application startup
requires:
  - T01: utils/logging.py with configure_logging(debug: bool)
affects: [S02, S03]
key_files:
  - main.py (added configure_logging call)
key_decisions:
  - configure_logging() called immediately after arg parsing, before any other operations
patterns_established:
  - Early logging initialization ensures all modules can use loggers immediately
drill_down_paths:
  - .gsd/milestones/M001/slices/S01/S01-PLAN.md
duration: 10min
verification_result: pass
completed_at: 2026-03-15T13:50:00Z
---

# T02: Wire --debug flag to logging in main.py

Connected the --debug CLI flag to the logging infrastructure.

## What Happened

Simple, surgical change: added one import and one function call in `cli()` right after argument parsing:

```python
from utils.logging import configure_logging
configure_logging(debug=args.debug)
```

This ensures logging is configured before any other operations, so all subsequent modules (plugins, services, commands) can immediately use loggers when imported.

## Deviations

None.

## Files Created/Modified

- `main.py` — Added configure_logging import and call (2 lines added)

## What's Ready for S02

- Running `ani-tupi --debug` activates DEBUG-level logging
- Debug logs write to `~/.local/state/ani-tupi/debug.log` as JSON
- Running without `--debug` keeps console clean
- All logging infrastructure from T01 is wired and active
