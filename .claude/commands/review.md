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

### Layered Architecture
1. **Routes = HTTP only** — `routes.py` must not contain business logic. No direct model calls, no audio ops.
2. **RecordingService owns orchestration** — start/stop/transcribe/correct/save all in `services/recording.py`.
3. **DI via app.state** — routes use `Depends(get_service)`, never import RecordingService directly at module scope.
4. **Mode race condition** — in `RecordingService.stop()`, `active_mode` captured once before any `await`.

### MLX / GPU
5. **MLX thread safety** — GPU ops in `run_in_executor(_mlx_executor, ...)`, not raw async.
6. **Metal cache** — `mx.metal.clear_cache()` after every inference call.
7. **No blocking in async** — `time.sleep`, model loading, file I/O must use executor.
8. **Lazy loading** — models loaded in `_ensure_model_loaded()`, not at module import.

### General
9. **Logging** — `logger = logging.getLogger(__name__)`, no `print()`.
10. **Server mode** — does the change work with `BACKEND_MODE=server`?

## Swift App Checks

### MVVM
1. **Business logic location** — new logic in `AppViewModel`, never in `MenuBarController` or views.
2. **Protocol first** — new backend calls added to `BackendServiceProtocol` before `BackendService`.
3. **AppDelegate = lifecycle** — no recording state, no business decisions in `AppDelegate`.

### Async / Safety
4. **Server URL** — no hardcoded `127.0.0.1`, must read from `UserDefaults`/`@AppStorage`.
5. **Actor isolation** — `BackendService` is `actor`, UI updates on `@MainActor`.
6. **Error handling** — no silent `try?` on critical paths (recording, paste).
7. **Accessibility** — `AXIsProcessTrusted()` checked before paste.
8. **No force unwrap** — especially URL construction.

## Both Modes

Any backend API change must be reflected in:
- Python backend (`routes.py` + `RecordingService` if needed)
- Swift `BackendServiceProtocol` + `BackendService.swift`
- `docs/backend-architecture.md` (if API contract changes)

## Output

CRITICAL → must fix
WARNING → should fix
INFO → optional

Ask if I should auto-fix.
