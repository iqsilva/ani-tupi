# Requirements

This file is the explicit capability and coverage contract for the project.

## Active

### R001 — Debug Flag Enables Full Execution Tracing
- Class: core-capability
- Status: active
- Description: `--debug` flag activates DEBUG-level logging that captures every significant operation (function calls, variable values, HTTP responses, state changes) in structured JSON format
- Why it matters: AI agents need complete visibility into app behavior for offline analysis and troubleshooting without reading source code
- Source: user
- Primary owning slice: M001/S01
- Supporting slices: M001/S02, M001/S03
- Validation: unmapped
- Notes: JSON format chosen over text for agent parseability; human readability secondary

### R002 — Sensitive Data Masking
- Class: security
- Status: active
- Description: API tokens, passwords, auth headers, and other credentials are automatically redacted in debug logs
- Why it matters: Debug logs may be shared with agents or stored; credentials must not leak
- Source: user
- Primary owning slice: M001/S01
- Supporting slices: M001/S02
- Validation: unmapped
- Notes: Masking patterns applied at logger level, not per-statement

### R003 — Debug Log Persistence and Rotation
- Class: operability
- Status: active
- Description: Debug logs write to `~/.local/state/ani-tupi/debug.log` with automatic rotation; latest file always available for agent access
- Why it matters: Persistent trace allows post-mortem analysis and agent review without live session access
- Source: user
- Primary owning slice: M001/S01
- Supporting slices: none
- Validation: unmapped
- Notes: Rotation keeps latest file current; older files compressed and retained

### R004 — Print Statements Replaced with Loguru Logger
- Class: core-capability
- Status: active
- Description: All internal `print()` calls (debug info, API traces, decisions) are replaced with loguru logger calls; UI output preserved unchanged
- Why it matters: Consolidates all execution tracing through structured logging; eliminates ad-hoc printing that makes tracing fragile
- Source: user
- Primary owning slice: M001/S02
- Supporting slices: none
- Validation: unmapped
- Notes: UI output (prompts, menus, results) remains as intentional stdout/stderr, not logged

### R005 — Full Execution Trace Completeness
- Class: core-capability
- Status: active
- Description: Debug log captures function entry/exit, variable values passed to key functions, complete HTTP request/response bodies (masked), API call outcomes, cache hits/misses, and decision branches
- Why it matters: Agent reasoning depends on complete trace—missing steps create gaps that require code reading
- Source: user
- Primary owning slice: M001/S02
- Primary owning slice: M001/S03
- Validation: unmapped
- Notes: Exceptions capture full tracebacks; API responses logged even on success for pattern analysis

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| R001 | core-capability | active | M001/S01 | M001/S02, M001/S03 | mapped |
| R002 | security | active | M001/S01 | M001/S02 | mapped |
| R003 | operability | active | M001/S01 | none | mapped |
| R004 | core-capability | active | M001/S02 | none | mapped |
| R005 | core-capability | active | M001/S02 | M001/S03 | mapped |

## Coverage Summary

- Active requirements: 5
- Mapped to slices: 5
- Validated: 0
- Unmapped active requirements: 0
