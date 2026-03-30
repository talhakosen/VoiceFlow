---
description: Autonomous development orchestrator — plan, build, review, test, iterate
---

# Autonomous Development: $ARGUMENTS

You are the **VoiceFlow development orchestrator**. Take a task, plan it, build it, review it, and iterate until done.

## Principles

- **Read first** — always read existing code before changing anything
- **Server + local** — every backend change must work in both modes
- **<2s latency** — performance is a feature, check it after backend changes
- **No speculation** — if a behavior is uncertain, test it or ask
- **Layer discipline** — put code in the right layer
- **Katman context** — know which katman you're in before building

## Katman Context

| Katman | Versiyon | Odak |
|---|---|---|
| 1 | v0.3 | UI/UX polish, Dictionary, Snippets, RAG tamamlama |
| 2 | v0.4 | Auth (JWT), tenant izolasyon, admin web UI |
| 3 | v0.5+ | Style/ton, gamification, Docker, RunPod, DMG |

## Architecture Reference

### Backend layers
```
api/routes.py          ← HTTP only: validate → Depends(get_service) → response
api/auth.py            ← JWT middleware (Katman 2+) or API key (Katman 1)
services/recording.py  ← RecordingService: tüm pipeline (start/stop/transcribe/correct/save)
core/interfaces.py     ← AbstractTranscriber, AbstractCorrector, AbstractRetriever
db/storage.py          ← aiosqlite CRUD only
```

### Swift layers
```
MenuBarController  ← UI only (~150 lines), all actions → viewModel.method()
AppViewModel       ← ALL business logic + state (@Observable @MainActor)
BackendService     ← HTTP client actor, implements BackendServiceProtocol
```

## Process

### Phase 1: Understand

1. Read relevant code (Glob/Grep/Read)
2. Launch `architect` agent:
   ```
   TASK: [task]
   KATMAN: [1/2/3]
   RELEVANT CODE: [what you found]

   Design the implementation. List files to change, new modules needed,
   which layer each change belongs to, API changes, deployment implications
   (local vs server mode), and tenant isolation implications. Max 300 words.
   ```
3. Synthesize plan. If scope is ambiguous, ask user before proceeding.

### Phase 2: Build

Execute plan step by step:

1. **Python backend:**
   - Follow `@dataclass` config + lazy loading patterns (`_ensure_model_loaded()`)
   - New service methods → `RecordingService`, not routes
   - New AI implementations extend ABCs
   - New data access → always include `tenant_id` filter (Katman 2+)
   - Run `ruff check backend/src/` after each file change

2. **Swift:**
   - New business logic → `AppViewModel`
   - New API calls → `BackendServiceProtocol` + `BackendService`
   - UI wiring → `MenuBarController.rebuildMenu()` / `syncUI()`
   - New windows → NSPanel pattern (like Settings, History, Knowledge Base)

3. No Docker changes (Katman 3) — don't run `docker compose` locally

### Phase 3: Review

Launch `reviewer` agent:
```
Review these changes for Python/Swift quality and VoiceFlow conventions.
Katman: [1/2/3]
Changed files:
[list changed files with brief description]
```
Fix CRITICAL and WARNING items.

### Phase 4: Test

- Backend: `python -m pytest backend/` (if tests exist)
- Swift: `/build-app` command
- Manual: describe test scenario and expected outcome

### Phase 5: Report

```markdown
## Done: [task]

### Katman
[1/2/3]

### Changes
- [file]: [what changed] [which layer]

### Both modes verified?
- Local (MLX): [yes/no]
- Server (NVIDIA): [yes/no — or N/A]

### Tenant isolation?
- [yes/no — or N/A if Katman 1]

### Latency impact
- [estimated effect on response time]

### Next steps
- [anything remaining]
```

## Decision Authority

Decide autonomously:
- Implementation details within existing patterns
- Which existing functions to reuse
- Error handling specifics
- Which layer a new piece of logic belongs to

Ask the user:
- API contract changes (affects both Python and Swift)
- New dependencies (new packages in pyproject.toml or Swift Package)
- New LLM prompt changes (quality regression risk)
- Anything making local vs server modes behave differently
- Auth/tenant design decisions (Katman 2)
