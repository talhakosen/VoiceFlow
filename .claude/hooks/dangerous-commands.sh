#!/bin/bash
# PreToolUse Hook — Block dangerous commands
set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if echo "$COMMAND" | grep -qE 'git reset --hard'; then
  echo "BLOCKED: 'git reset --hard' commit edilmemiş değişiklikleri siler!" >&2
  exit 2
fi

if echo "$COMMAND" | grep -qE 'git push.*--force|git push.*-f\b'; then
  echo "BLOCKED: 'git push --force' remote history'yi değiştirir!" >&2
  exit 2
fi

if echo "$COMMAND" | grep -qE 'rm\s+-rf\s+/|rm\s+-rf\s+\.\s*$'; then
  echo "BLOCKED: 'rm -rf' tehlikeli!" >&2
  exit 2
fi

if echo "$COMMAND" | grep -qE 'docker system prune -a'; then
  echo "BLOCKED: 'docker system prune -a' tüm image'ları siler — model cache'i kaybedersin!" >&2
  exit 2
fi

if echo "$COMMAND" | grep -qE 'pkill.*python|kill.*uvicorn' && echo "$COMMAND" | grep -qE '\-9'; then
  echo "BLOCKED: Python backend'i SIGKILL ile öldürme — önce 'voiceflow.sh stop' dene" >&2
  exit 2
fi

exit 0
