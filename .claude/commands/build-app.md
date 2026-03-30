---
description: Build and deploy Swift macOS app to /Applications
---

# Build VoiceFlow Mac App

Run the full clean build and deploy sequence. No shortcuts — DerivedData must be cleared.

```bash
pkill -f "VoiceFlow.app" 2>/dev/null || true
rm -rf ~/Library/Developer/Xcode/DerivedData/VoiceFlowApp-*
xcodebuild -project VoiceFlowApp/VoiceFlowApp.xcodeproj \
           -scheme VoiceFlowApp \
           -configuration Debug \
           clean build
rm -rf /Applications/VoiceFlow.app
cp -R ~/Library/Developer/Xcode/DerivedData/VoiceFlowApp-*/Build/Products/Debug/VoiceFlow.app \
      /Applications/
open /Applications/VoiceFlow.app
```

## After Build

Remind the user:
> **Accessibility izni sıfırlandı.** System Settings → Privacy & Security → Accessibility → VoiceFlow'u etkinleştir.

This is required every time the binary changes. Auto-paste fails silently without it.

## If Build Fails

1. Read the full error — don't guess
2. Check `xcodebuild` output for the actual failing file and line
3. Common issues:
   - Missing entitlement: check `VoiceFlowApp.entitlements`
   - Signing: Debug builds don't need signing, check scheme settings
   - Swift version mismatch: check `SWIFT_VERSION` in project settings
