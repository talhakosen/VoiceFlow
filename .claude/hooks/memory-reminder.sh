#!/bin/bash
# Stop Hook — Remind to update docs if significant changes were made
set -euo pipefail

ALL_CHANGES=$(git diff --name-only HEAD 2>/dev/null || git diff --name-only 2>/dev/null || true)

if [ -z "$ALL_CHANGES" ]; then
  exit 0
fi

REMINDERS=""

# Python backend changes → check if docs/backend-architecture.md needs update
# Only care about core src/ changes, not scripts/training or scripts/data_gen
PY_CHANGES=$(echo "$ALL_CHANGES" | grep -E 'backend/src/.*\.py$' || true)
if [ -n "$PY_CHANGES" ]; then
  PY_COUNT=$(echo "$PY_CHANGES" | wc -l | tr -d ' ')
  DOCS_FILE="$CLAUDE_PROJECT_DIR/docs/architecture/backend-architecture.md"
  if [ -f "$DOCS_FILE" ]; then
    DOCS_MOD=$(stat -f %m "$DOCS_FILE" 2>/dev/null || stat -c %Y "$DOCS_FILE" 2>/dev/null || echo "0")
    NOW=$(date +%s)
    DOCS_AGE=$(( NOW - DOCS_MOD ))
    if [ "$DOCS_AGE" -gt 3600 ] && [ "$PY_COUNT" -gt 2 ]; then
      REMINDERS="${REMINDERS}
- docs/architecture/backend-architecture.md: ${PY_COUNT} Python dosyası değişti — API/mimari güncel mi?"
    fi
  fi
fi

# Swift changes → check if docs/app-architecture.md needs update
SWIFT_CHANGES=$(echo "$ALL_CHANGES" | grep -E '\.swift$' || true)
if [ -n "$SWIFT_CHANGES" ]; then
  SWIFT_COUNT=$(echo "$SWIFT_CHANGES" | wc -l | tr -d ' ')
  DOCS_FILE="$CLAUDE_PROJECT_DIR/docs/architecture/app-architecture.md"
  if [ -f "$DOCS_FILE" ]; then
    DOCS_MOD=$(stat -f %m "$DOCS_FILE" 2>/dev/null || stat -c %Y "$DOCS_FILE" 2>/dev/null || echo "0")
    NOW=$(date +%s)
    DOCS_AGE=$(( NOW - DOCS_MOD ))
    if [ "$DOCS_AGE" -gt 3600 ] && [ "$SWIFT_COUNT" -gt 1 ]; then
      REMINDERS="${REMINDERS}
- docs/architecture/app-architecture.md: ${SWIFT_COUNT} Swift dosyası değişti — güncel mi?"
    fi
  fi
fi

# develop-plan.md — check if any completed tasks weren't marked
PLAN_FILE="$CLAUDE_PROJECT_DIR/.claude/develop-plan.md"
if [ -f "$PLAN_FILE" ]; then
  PLAN_MOD=$(stat -f %m "$PLAN_FILE" 2>/dev/null || stat -c %Y "$PLAN_FILE" 2>/dev/null || echo "0")
  NOW=$(date +%s)
  PLAN_AGE=$(( NOW - PLAN_MOD ))
  ALL_PY=$(echo "$ALL_CHANGES" | grep -E '\.py$' || true)
  if [ "$PLAN_AGE" -gt 7200 ] && [ -n "$ALL_PY" ]; then
    REMINDERS="${REMINDERS}
- .claude/develop-plan.md: Tamamlanan task'ları [DONE] olarak işaretle"
  fi
fi

if [ -n "$REMINDERS" ]; then
  echo "DOCS GÜNCELLE:${REMINDERS}" >&2
  exit 2
fi

exit 0
