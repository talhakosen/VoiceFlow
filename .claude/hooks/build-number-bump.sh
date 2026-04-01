#!/bin/bash
# PreToolUse Hook — Auto-increment build number + patch version before xcodebuild

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only run for xcodebuild commands
if ! echo "$COMMAND" | grep -q "xcodebuild"; then
  exit 0
fi

PLIST="$CLAUDE_PROJECT_DIR/VoiceFlowApp/Resources/Info.plist"

if [ ! -f "$PLIST" ]; then
    exit 0
fi

# Increment CFBundleVersion (build number)
CURRENT_BUILD=$(/usr/libexec/PlistBuddy -c "Print CFBundleVersion" "$PLIST" 2>/dev/null)
if [ -z "$CURRENT_BUILD" ]; then exit 0; fi
NEXT_BUILD=$((CURRENT_BUILD + 1))
/usr/libexec/PlistBuddy -c "Set CFBundleVersion $NEXT_BUILD" "$PLIST"

# Increment patch in CFBundleShortVersionString (e.g. 1.0.3 → 1.0.4)
CURRENT_VERSION=$(/usr/libexec/PlistBuddy -c "Print CFBundleShortVersionString" "$PLIST" 2>/dev/null)
MAJOR=$(echo "$CURRENT_VERSION" | cut -d. -f1)
MINOR=$(echo "$CURRENT_VERSION" | cut -d. -f2)
PATCH=$(echo "$CURRENT_VERSION" | cut -d. -f3)
NEXT_PATCH=$((PATCH + 1))
NEXT_VERSION="$MAJOR.$MINOR.$NEXT_PATCH"
/usr/libexec/PlistBuddy -c "Set CFBundleShortVersionString $NEXT_VERSION" "$PLIST"

echo "Version: $CURRENT_VERSION ($CURRENT_BUILD) → $NEXT_VERSION ($NEXT_BUILD)"
