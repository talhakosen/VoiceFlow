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
Scopes: `backend`, `app`, `docker`, `ml`, `docs`, `rag`, `context`

## Examples

```
feat(backend): add RecordingService with constructor injection

- AbstractTranscriber/AbstractCorrector ABCs in core/interfaces.py
- RecordingService orchestrates transcribe+correct+save pipeline
- routes.py reduced to ~100 lines, zero business logic
- app.state DI via Depends(get_service)

feat(app): add AppViewModel with MVVM pattern

- @Observable @MainActor AppViewModel owns all state + business logic
- MenuBarController reduced to UI-only (~200 lines)
- BackendServiceProtocol for mock injection in tests

feat(rag): add ChromaDB context engine

- PersistentClient with tenant=company_id isolation
- MiniLM embeddings, top-3 retrieval
- RecordingService.stop() injects retrieved context before LLM call
```

## After Commit

Check if `docs/` needs updating:
- Architecture change? → `docs/architecture.md`
- New API endpoint? → `docs/backend-architecture.md`
- New app feature? → `docs/app-architecture.md`
- New phase complete? → `docs/enterprise-strategy.md` roadmap
