# VoiceFlow — VS Code Integration

VoiceFlow supports a custom URL scheme (`voiceflow://`) for triggering recording from any app, including VS Code.

## URL Scheme

| URL | Action |
|-----|--------|
| `voiceflow://start` | Start recording |
| `voiceflow://stop` | Stop recording and paste transcription |
| `voiceflow://toggle` | Toggle recording on/off |

The macOS app registers these handlers via `LSApplicationQueriesSchemes` in `Info.plist`.

## VS Code Keybindings

Add to `~/.config/Code/User/keybindings.json` (or via **Preferences: Open Keyboard Shortcuts (JSON)**):

```json
[
  {
    "key": "ctrl+shift+r",
    "command": "workbench.action.terminal.runSelectedText",
    "when": "false"
  },
  {
    "key": "ctrl+shift+r",
    "command": "workbench.action.openWith",
    "args": { "scheme": "voiceflow", "authority": "start" }
  }
]
```

Or use the simpler shell-based approach with VS Code tasks:

### `.vscode/tasks.json`

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "VoiceFlow: Start",
      "type": "shell",
      "command": "open 'voiceflow://start'",
      "presentation": { "reveal": "never" },
      "group": "none"
    },
    {
      "label": "VoiceFlow: Stop",
      "type": "shell",
      "command": "open 'voiceflow://stop'",
      "presentation": { "reveal": "never" },
      "group": "none"
    }
  ]
}
```

Then bind the tasks to keys in `keybindings.json`:

```json
[
  {
    "key": "ctrl+shift+[",
    "command": "workbench.action.tasks.runTask",
    "args": "VoiceFlow: Start"
  },
  {
    "key": "ctrl+shift+]",
    "command": "workbench.action.tasks.runTask",
    "args": "VoiceFlow: Stop"
  }
]
```

## Engineering Mode + Output Format

Before dictating, set engineering mode and output format via the REST API:

```bash
# Switch to engineering mode with PR description output
curl -s -X POST http://127.0.0.1:8765/api/config \
  -H "Content-Type: application/json" \
  -d '{"mode": "engineering", "output_format": "pr_description"}'
```

Available `output_format` values:
- `prose` — plain corrected text (default)
- `code_comment` — output formatted as `// comment`
- `pr_description` — GitHub PR markdown (## Summary, ## Changes)
- `jira_ticket` — Jira-style (*Summary:*, *Description:*, *Acceptance Criteria:*)
