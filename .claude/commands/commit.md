---
description: Commit staged changes and update develop-plan.md
---

# Commit Changes

1. Review staged changes: `git diff --cached`
2. Write a conventional commit message
3. Update `.claude/develop-plan.md`:
   - Mark completed items with `[DONE YYYY-MM-DD]`
   - Add new items discovered during implementation
   - Update "Şu An Çalışan" section if new features ship
4. Commit everything together

## Commit Message Format

```
type(scope): short description

- detail 1
- detail 2

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

Types: `feat`, `fix`, `refactor`, `docs`, `chore`, `perf`
Scopes: `backend`, `app`, `docker`, `ml`, `docs`

## Examples

```
feat(backend): add server mode with faster-whisper and Ollama

- BACKEND_MODE=server binds 0.0.0.0 and uses NVIDIA stack
- API key auth middleware on all /api/* endpoints
- faster-whisper replaces mlx-whisper when mode=server

feat(app): make server URL configurable via Settings

- @AppStorage("serverURL") replaces hardcoded localhost
- Settings window shows URL + API key fields
- Local mode still uses embedded backend
```

## After Commit

Check if `docs/` needs updating:
- Architecture change? → update `docs/architecture.md`
- New API endpoint? → update `docs/backend-architecture.md`
- New app feature? → update `docs/app-architecture.md`
