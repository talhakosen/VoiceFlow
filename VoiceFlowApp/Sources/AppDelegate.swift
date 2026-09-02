import AppKit
import AVFoundation
import ComposableArchitecture
import SwiftUI

class AppDelegate: NSObject, NSApplicationDelegate {
    private var menuBarController: MenuBarController?
    private var recordingOverlay: RecordingOverlayWindow?
    private var onboardingWindow: NSWindow?
    private var loginWindow: NSPanel?
    private let trainingPillController = TrainingPillWindowController()
    private let modeIndicator = ModeIndicatorWindowController()

    // Tek örnek: TCA'daki BackendProcessClient de aynı manager'ı kullanır,
    // aksi halde restart butonu başka bir süreç nesnesini yönetirdi.
    private let backendManager = BackendProcessManager.shared

    let store = Store(initialState: AppFeature.State.fromUserDefaults()) { AppFeature() }

    private var storeObservation: Task<Void, Never>?
    private let hotkeyManager = HotkeyManager()

    // MARK: - Lifecycle

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Request Accessibility permission on launch — resets after every rebuild
        let opts = NSDictionary(object: true, forKey: "AXTrustedCheckOptionPrompt" as NSString)
        let trusted = AXIsProcessTrustedWithOptions(opts)
        BackendService.debugLog("Accessibility trusted: \(trusted)")

        ensureUserID()
        setupHotkeys()
        startStoreObservation()

        let mode = DeploymentMode(rawValue: UserDefaults.standard.string(forKey: AppSettings.deploymentMode) ?? "") ?? .local

        if mode == .server {
            NSLog("VoiceFlow: Server mode — skipping local backend startup")
            DispatchQueue.main.async {
                self.menuBarController = MenuBarController(store: self.store)
            }
        } else {
            // Backend ölürse kullanıcı bunu ancak dikte çalışmayınca anlıyordu.
            // Watchdog hem otomatik toparlar hem de durumu menüye yansıtır.
            backendManager.onStateChange = { [weak self] healthy, failure in
                guard let self else { return }
                if healthy {
                    self.store.send(.recording(.backendRestartFinished(true)))
                    self.reapplyInputDevice()
                } else {
                    let msg = failure?.message ?? "Servis yanıt vermiyor"
                    self.store.send(.recording(.recordingFailed("\(msg) — Zorla Yeniden Başlat")))
                }
            }
            backendManager.startFresh()
            backendManager.waitUntilReady { [weak self] success in
                DispatchQueue.main.async {
                    guard let self else { return }
                    NSLog("VoiceFlow: Backend %@", success ? "ready" : "may not be ready")
                    if !success {
                        let detail = self.backendManager.lastFailure?.message ?? "Servis başlatılamadı"
                        self.store.send(.recording(.recordingFailed("\(detail) — Yeniden Başlat'a bas")))
                    }
                    self.menuBarController = MenuBarController(store: self.store)
                    self.backendManager.startWatchdog()
                    if success { self.reapplyInputDevice() }
                }
            }
        }

        requestAccessibilityPermission()
        requestMicrophonePermission()
        handleAuthFlow(deploymentMode: mode)
    }

    func applicationWillTerminate(_ notification: Notification) {
        backendManager.stopWatchdog()
        backendManager.invalidateHealthTimer()
        storeObservation?.cancel()
        hotkeyManager.stop()
        backendManager.stop()
    }

    /// Backend süreci mikrofon tercihini hafızada tutuyor — her yeniden
    /// başlatmada (watchdog dahil) sıfırlanır, o yüzden tekrar göndeririz.
    private func reapplyInputDevice() {
        let name = UserDefaults.standard.string(forKey: AppSettings.inputDevice) ?? ""
        guard !name.isEmpty else { return }
        store.send(.recording(.setInputDevice(name)))
        NSLog("VoiceFlow: Re-applied input device: %@", name)
    }

    // MARK: - Hotkey Wiring

    private func setupHotkeys() {
        hotkeyManager.onStartRecording = { [weak self] in
            self?.store.send(.recording(.startRecording))
        }
        hotkeyManager.onStopRecording = { [weak self] in
            self?.store.send(.recording(.stopRecording))
            // Monitor refresh moved to polling loop — happens after processing completes,
            // not immediately after stop. This prevents stale fn=true events during processing.
        }
        hotkeyManager.onModeSwitch = { [weak self] mode in
            self?.store.send(.recording(.selectAppMode(mode)))
        }
        hotkeyManager.start()
    }

    // MARK: - Store Observation (Polling)

    private func startStoreObservation() {
        let overlay = RecordingOverlayWindow()
        self.recordingOverlay = overlay

        storeObservation = Task { @MainActor [weak self] in
            guard let self else { return }
            var prevRecording = false
            var prevProcessing = false
            var prevShowPill = false
            var prevMode: AppMode = .general

            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
                let recState = self.store.recording
                let isRecording = recState.isRecording
                let isProcessing = recState.isProcessing
                let showPill = self.store.training.isVisible
                let mode = recState.currentAppMode

                // Sync processing state — blocks fnDown while backend is transcribing
                self.hotkeyManager.setProcessing(isProcessing)

                if prevProcessing && !isProcessing {
                    BackendService.debugLog("AppDelegate poll: processing done — trainingEnabled=\(recState.trainingModeEnabled) showPill=\(showPill) training.isVisible=\(self.store.training.isVisible)")
                    // Refresh monitors AFTER processing completes (not after stop).
                    // macOS sometimes stops delivering fn=true events; re-registering fixes it.
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { [weak self] in
                        self?.hotkeyManager.start()
                    }
                }

                // Keep HotkeyManager in sync with TCA truth to prevent stuck state
                self.hotkeyManager.syncRecordingState(isRecording)

                if isRecording && !prevRecording {
                    overlay.showRecording()
                    self.modeIndicator.showPersistent(mode: mode)
                } else if isProcessing && !prevProcessing {
                    overlay.showProcessing()
                    self.modeIndicator.close()
                } else if !isRecording && !isProcessing && (prevRecording || prevProcessing) {
                    overlay.hide()
                    self.modeIndicator.close()
                }

                if mode != prevMode && !isRecording {
                    self.modeIndicator.showBriefly(mode: mode)
                }

                if showPill && !prevShowPill {
                    BackendService.debugLog("AppDelegate: training.isVisible → TRUE, showing pill")
                    self.trainingPillController.show(store: self.store)
                } else if !showPill && prevShowPill {
                    BackendService.debugLog("AppDelegate: training.isVisible → FALSE, closing pill")
                    self.trainingPillController.close()
                }

                prevRecording = isRecording
                prevProcessing = isProcessing
                prevShowPill = showPill
                prevMode = mode
            }
        }
    }

    // MARK: - Auth Flow

    private func handleAuthFlow(deploymentMode: DeploymentMode) {
        if deploymentMode == .server {
            store.send(.auth(.tokenRefreshAttempted))
            Task { @MainActor [weak self] in
                guard let self else { return }
                try? await Task.sleep(nanoseconds: 300_000_000)
                if !self.store.auth.isLoggedIn {
                    self.showLoginWindow()
                }
                while !self.store.auth.isLoggedIn {
                    try? await Task.sleep(nanoseconds: 200_000_000)
                }
                self.loginWindow?.close()
                self.loginWindow = nil
                self.showOnboardingIfNeeded()
            }
        } else {
            showOnboardingIfNeeded()
        }
    }

    // MARK: - Windows

    private func showLoginWindow() {
        let authStore = store.scope(state: \.auth, action: \.auth)
        let hosting = NSHostingController(rootView: LoginView(store: authStore))
        let panel = NSPanel(
            contentRect: NSRect(origin: .zero, size: VFLayout.WindowSize.login),
            styleMask: [.titled, .fullSizeContentView, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        panel.contentViewController = hosting
        panel.title = "VoiceFlow Giriş"
        panel.isReleasedWhenClosed = false
        panel.isMovableByWindowBackground = true
        panel.center()
        panel.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        loginWindow = panel
    }

    private func showOnboardingIfNeeded() {
        let complete = UserDefaults.standard.bool(forKey: AppSettings.onboardingComplete)
        guard !complete else { return }

        let view = OnboardingView(onComplete: { [weak self] in
            self?.onboardingWindow?.close()
            self?.onboardingWindow = nil
        })
        let hosting = NSHostingController(rootView: view)
        let window = NSWindow(
            contentRect: NSRect(origin: .zero, size: VFLayout.WindowSize.onboarding),
            styleMask: [.titled, .closable],
            backing: .buffered,
            defer: false
        )
        window.contentViewController = hosting
        window.title = "VoiceFlow'a Hoş Geldiniz"
        window.isReleasedWhenClosed = false
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        onboardingWindow = window
    }

    // MARK: - User Identity

    private func ensureUserID() {
        let key = AppSettings.userID
        if UserDefaults.standard.string(forKey: key)?.isEmpty ?? true {
            let newID = UUID().uuidString
            UserDefaults.standard.set(newID, forKey: key)
            NSLog("VoiceFlow: Generated user ID: %@", newID)
        }
    }

    // MARK: - Permissions

    /// Mikrofonu Python backend'i açıyor ama TCC izni SORUMLU sürece (bu app'e)
    /// yazılıyor. App hiç izin istemezse macOS prompt göstermiyor ve CoreAudio
    /// hata yerine sessizce SIFIR örnek döndürüyor — kullanıcı "kayıt oluyor ama
    /// panoya bir şey gelmiyor" görüyor. Her rebuild imzayı değiştirdiği için
    /// izin sıfırlanıyor; Accessibility gibi bunu da açıkça istemek zorundayız.
    private func requestMicrophonePermission() {
        switch AVCaptureDevice.authorizationStatus(for: .audio) {
        case .authorized:
            NSLog("VoiceFlow: Microphone permission GRANTED")

        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .audio) { [weak self] granted in
                NSLog("VoiceFlow: Microphone permission %@", granted ? "GRANTED" : "DENIED")
                if !granted { self?.warnMicrophoneDenied() }
            }

        case .denied, .restricted:
            NSLog("VoiceFlow: Microphone permission DENIED — dictation will record silence")
            warnMicrophoneDenied()

        @unknown default:
            break
        }
    }

    private func warnMicrophoneDenied() {
        DispatchQueue.main.async { [weak self] in
            self?.store.send(.recording(.recordingFailed(
                "Mikrofon izni yok — Sistem Ayarları > Gizlilik > Mikrofon"
            )))
        }
    }

    private func requestAccessibilityPermission() {
        let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true]
        let accessEnabled = AXIsProcessTrustedWithOptions(options as CFDictionary)

        if accessEnabled {
            NSLog("VoiceFlow: Accessibility permission GRANTED")
        } else {
            NSLog("VoiceFlow: Accessibility permission NOT granted - auto-paste will not work!")
            NSLog("VoiceFlow: Go to System Settings > Privacy & Security > Accessibility > Enable VoiceFlow")
        }
    }
}
