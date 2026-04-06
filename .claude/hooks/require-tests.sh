#!/bin/bash
# PreToolUse Hook — Block git commit if backend src changes have no test coverage
set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only intercept git commit commands
if ! echo "$COMMAND" | grep -qE 'git commit'; then
  exit 0
fi

# Get staged files
STAGED=$(git -C "$CLAUDE_PROJECT_DIR" diff --name-only --cached 2>/dev/null || true)

if [ -z "$STAGED" ]; then
  exit 0
fi

# Backend src Python files changed (excluding __init__.py and config/cli)
SRC_CHANGED=$(echo "$STAGED" | grep -E 'backend/src/voiceflow/.*\.py$' | grep -vE '__init__\.py$|cli\.py$|config\.py$' || true)

if [ -z "$SRC_CHANGED" ]; then
  exit 0
fi

# Check if any test file is staged
TESTS_STAGED=$(echo "$STAGED" | grep -E 'backend/tests/test_.*\.py$' || true)

if [ -n "$TESTS_STAGED" ]; then
  exit 0
fi

# Build readable list of changed src files
SRC_LIST=$(echo "$SRC_CHANGED" | sed 's|backend/src/voiceflow/||g' | tr '\n' ', ' | sed 's/, $//')

echo "BLOCKED: Test yazılmadan commit yapılamaz!

Değiştirilen backend dosyaları:
$(echo "$SRC_CHANGED" | sed 's/^/  - /')

backend/tests/test_*.py kapsamında hiç test staged değil.

Seçenekler:
  1. İlgili test dosyasını yaz/güncelle ve stage'e ekle
  2. Sadece refactor/doc değişikliğiyse: git commit --no-verify (bilinçli bypass)" >&2

exit 2
