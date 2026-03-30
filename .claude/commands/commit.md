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
Scopes: `backend`, `app`, `docker`, `ml`, `docs`, `rag`, `auth`, `ui`, `dict`, `snippets`

## Examples

```
feat(ui): simplify menu bar and add 2-panel Settings window

- Menu reduced to 5 items (Status, Toggle, Force Stop, Settings, Quit)
- Settings: 2-panel with General/Recording/Knowledge Base/Account/About
- Language, mode, correction moved from menu to Settings

feat(dict): add user dictionary with post-processing substitution

- SQLite user_dictionary table (trigger → replacement, personal/team scope)
- Dictionary substitution pass after Whisper, before LLM correction
- Mac app: Settings → General → Dictionary section

feat(auth): add JWT authentication and tenant isolation

- POST /auth/login returns JWT access + refresh tokens
- JWT middleware on all /api/* routes (extracts user_id + tenant_id)
- SQLite queries filtered by tenant_id from JWT payload
- Swift: login view, Keychain token storage
```

## After Commit

Check if `docs/` needs updating:
- Architecture change? → `docs/architecture.md`
- New API endpoint? → `docs/backend-architecture.md`
- New app feature? → `docs/app-architecture.md`
- Katman completed? → `docs/enterprise-strategy.md` roadmap güncelle
- Competitor positioning changed? → `docs/research-wispr-flow.md`
