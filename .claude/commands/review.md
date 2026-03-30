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
1. **Routes = HTTP only** — `routes.py` must not contain business logic.
2. **RecordingService owns orchestration** — all pipeline logic in `services/recording.py`.
3. **DI via app.state** — routes use `Depends(get_service)`, never import service directly.
4. **Mode race condition** — `active_mode` captured before any `await` in `stop()`.
5. **Tenant isolation** — new data queries include `WHERE tenant_id = ?` (Katman 2+).

### MLX / GPU
6. **MLX thread safety** — GPU ops via `run_in_executor(_mlx_executor, ...)`.
7. **Metal cache** — `mx.metal.clear_cache()` after every inference.
8. **No blocking in async** — `time.sleep`, model loading, file I/O use executor.
9. **Lazy loading** — models in `_ensure_model_loaded()`, not at module import.

### Auth (Katman 2+)
10. **JWT on all /api/* routes** — no endpoint bypasses middleware.
11. **Tenant ID from JWT** — never from request body (prevents spoofing).
12. **Passwords hashed** — bcrypt/argon2, never plaintext.
13. **No tokens in logs** — auth values never appear in `logger.*`.

### General
14. **Logging** — `logger = logging.getLogger(__name__)`, no `print()`.
15. **Server mode** — does the change work with `BACKEND_MODE=server`?

## Swift App Checks

### MVVM
1. **Business logic in AppViewModel** — never in MenuBarController or views.
2. **Protocol first** — new backend calls in `BackendServiceProtocol` before `BackendService`.
3. **AppDelegate = lifecycle** — no business decisions here.
4. **Menu ≤ 5 items** (Katman 1+) — all settings in Settings window, not menu.

### Async / Safety
5. **No hardcoded URLs** — `serverURL` from `@AppStorage`.
6. **Actor isolation** — `BackendService` is `actor`, UI updates on `@MainActor`.
7. **Error handling** — no silent `try?` on critical paths.
8. **Accessibility** — `AXIsProcessTrusted()` before paste.
9. **JWT in Keychain** (Katman 2+) — never in UserDefaults.

## Both Modes

Any backend API change must be reflected in:
- Python `routes.py` + `RecordingService` if needed
- Swift `BackendServiceProtocol` + `BackendService.swift`
- `docs/backend-architecture.md` if API contract changes

## Output

CRITICAL → must fix
WARNING → should fix
INFO → optional

Ask if I should auto-fix.
