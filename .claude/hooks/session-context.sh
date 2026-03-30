#!/bin/bash
# SessionStart Hook — Git context + current phase + plan status
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
LAST_COMMITS=$(git log --oneline -5 2>/dev/null || echo "no commits")
CHANGED_COUNT=$(git diff --name-only 2>/dev/null | grep -c . || echo "0")
STAGED_COUNT=$(git diff --cached --name-only 2>/dev/null | grep -c . || echo "0")
UNTRACKED_COUNT=$(git ls-files --others --exclude-standard 2>/dev/null | grep -c . || echo "0")

# ── Plan: extract next tasks from develop-plan.md ──
PLAN_FILE="$CLAUDE_PROJECT_DIR/.claude/develop-plan.md"
NEXT_TASKS=""
if [ -f "$PLAN_FILE" ]; then
  # Find first phase with unchecked items
  NEXT_TASKS=$(grep -E '^\- \[ \]' "$PLAN_FILE" | head -5 || echo "")
fi

# ── Current phase ──
CURRENT_PHASE=""
if [ -f "$PLAN_FILE" ]; then
  CURRENT_PHASE=$(grep -E '^## Phase' "$PLAN_FILE" | head -1 || echo "")
fi

# ── Memory: recently modified files ──
MEMORY_DIR="$HOME/.claude/projects/-Users-talhakosen-Developer-utils-voiceflow/memory"
LAST_MEMORY=""
if [ -d "$MEMORY_DIR" ]; then
  LAST_MEMORY=$(ls -t "$MEMORY_DIR"/*.md 2>/dev/null | head -3 | while read f; do
    FNAME=$(basename "$f")
    MTIME=$(stat -f '%Sm' -t '%d.%m %H:%M' "$f" 2>/dev/null || echo "?")
    echo "  - $FNAME ($MTIME)"
  done || echo "")
fi

# ── Build context ──
CONTEXT="## VoiceFlow Session Context
**Branch:** ${BRANCH}
**Son 5 commit:**
${LAST_COMMITS}
**Değişiklikler:** ${CHANGED_COUNT} modified, ${STAGED_COUNT} staged, ${UNTRACKED_COUNT} untracked"

if [ -n "$CURRENT_PHASE" ]; then
  CONTEXT="${CONTEXT}
**Güncel faz:** ${CURRENT_PHASE}"
fi

if [ -n "$NEXT_TASKS" ]; then
  CONTEXT="${CONTEXT}

## Sıradaki İşler (.claude/develop-plan.md)
${NEXT_TASKS}"
fi

if [ -n "$LAST_MEMORY" ]; then
  CONTEXT="${CONTEXT}

## Son Güncellenen Memory
${LAST_MEMORY}"
fi

if command -v jq &>/dev/null; then
  jq -n --arg ctx "$CONTEXT" '{
    hookSpecificOutput: {
      hookEventName: "SessionStart",
      additionalContext: $ctx
    }
  }'
else
  echo "$CONTEXT"
fi
