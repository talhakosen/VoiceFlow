---
description: Review code for VoiceFlow quality standards
---

# Code Review: $ARGUMENTS

Review `$ARGUMENTS` for VoiceFlow quality standards. If empty, review all files changed since last commit.

Determine changed files:
```bash
git diff --name-only HEAD 2>/dev/null || git diff --name-only
```

Launch `reviewer` agent with the changed files, then report findings.

## Python Backend Checks

1. **MLX thread safety** — GPU ops in `run_in_executor(_mlx_executor, ...)`, not raw async
2. **Metal cache** — `mx.metal.clear_cache()` after every inference call
3. **No blocking in async** — `time.sleep`, model loading, file I/O must use executor
4. **Lazy loading** — models loaded in `_ensure_model_loaded()`, not at module import
5. **Logging** — `logger = logging.getLogger(__name__)`, no `print()`
6. **Server mode** — does the change work with `BACKEND_MODE=server`?

## Swift App Checks

1. **Server URL** — no hardcoded `127.0.0.1`, must read from `UserDefaults`
2. **Actor isolation** — `BackendService` is `actor`, UI updates on `@MainActor`
3. **Error handling** — no silent `try?` on critical paths (recording, paste)
4. **Accessibility** — `AXIsProcessTrusted()` checked before paste

## Both Modes

Any backend API change must be reflected in:
- Python backend (`routes.py`)
- Swift `BackendService.swift` (matching struct/endpoint)
- `docs/backend-architecture.md` (if API contract changes)

## Output

CRITICAL → must fix
WARNING → should fix
INFO → optional

Ask if I should auto-fix.
