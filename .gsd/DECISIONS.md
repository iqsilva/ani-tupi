# Decisions Register

<!-- Append-only. Never edit or remove existing rows.
     To reverse a decision, add a new row that supersedes it.
     Read this file at the start of any planning or research phase. -->

| # | When | Scope | Decision | Choice | Rationale | Revisable? |
|---|------|-------|----------|--------|-----------|------------|
| D001 | M001 | logging | Log format | JSON lines | Machine-readable for agents; structured for parsing; human review still possible | Yes — if readability matters more than parseability |
| D002 | M001 | logging | Log output destination | stderr + file | Console for human visibility (if needed) + file for offline analysis; both flow from loguru config | No |
| D003 | M001 | logging | Debug log location | ~/.local/state/ani-tupi/debug.log | Consistent with existing cache/state location; XDG standard | No |
| D004 | M001 | logging | Log rotation | 50MB per file, keep latest | Prevents unbounded growth; keeps recent trace available; aligns with existing rotation patterns | Yes — if disk space becomes constraint |
| D005 | M001 | logging | Masking strategy | Pattern-based redaction at logger level | Bulletproof (applies to all output); centralized; no per-call decisions needed | No |
| D006 | M001 | logging | Function tracing scope | All I/O, API calls, decisions; skip trivial helpers | Full trace without noise; balances completeness and readability | Yes — if log becomes too noisy |
