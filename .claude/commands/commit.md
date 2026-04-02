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
- Architecture change? → `docs/architecture/architecture.md`
- New API endpoint? → `docs/architecture/backend-architecture.md`
- New app feature? → `docs/architecture/app-architecture.md`
- Katman completed? → `docs/enterprise/enterprise-strategy.md` roadmap güncelle
- Competitor positioning changed? → `docs/enterprise/research-wispr-flow.md`
- ML/training change? → `docs/ml/runpod-finetuning.md` veya `docs/ml/fine-tuning-plan.md`

## Trello Güncelleme

Her commit sonrası Trello board'u güncelle (Board: `Omhc3R8e`):

1. **Tamamlanan kart varsa** → Done listesine taşı (`idList: 69cab079656e54941cc4572e`)
2. **Checklist item'ları** → tamamlananları `state=complete` yap
3. **Yeni bir şey keşfedildiyse** → Backlog'a kart ekle

```
Board  : Omhc3R8e
Key    : 642cb17e41836ea0e33f92ff7bf17199
Token  : ATTA1b2d6f3227ec8fb10feb07aba20675de3433c0a3da4ffa519ebe2f86bb0906a803B94A13

Lists:
  Backlog     : 69cab0784259d48aad42caf1
  In Progress : 69cab07826e56dbf8d1cf44f
  Done        : 69cab079656e54941cc4572e
```

Kart taşıma:
```bash
curl -s -X PUT "https://api.trello.com/1/cards/{CARD_ID}?key=KEY&token=TOKEN&idList=DONE_LIST_ID"
```

Checklist item tamamlama:
```bash
curl -s -X PUT "https://api.trello.com/1/cards/{CARD_ID}/checkItem/{ITEM_ID}?key=KEY&token=TOKEN&state=complete"
```
