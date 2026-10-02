import ComposableArchitecture
import SwiftUI
import AppKit

// MARK: - Window access helper

struct HostingWindowFinder: NSViewRepresentable {
    var callback: (NSWindow?) -> Void
    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        DispatchQueue.main.async { self.callback(view.window) }
        return view
    }
    func updateNSView(_ nsView: NSView, context: Context) {}
}

extension View {
    func withHostingWindowCallback(_ callback: @escaping (NSWindow?) -> Void) -> some View {
        background(HostingWindowFinder(callback: callback))
    }
}

// MARK: - Main Content Section (Ana pencere nav — Home + feature sections)

enum MainContentSection: String, Identifiable {
    case home        = "Ana Ekran"
    case dictionary  = "Sözlük"
    case knowledge   = "Proje Terimleri"
    case recording   = "Kayıt"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .home:       return "house"
        case .dictionary: return VFIcon.dictionary
        case .knowledge:  return VFIcon.knowledgeBase
        case .recording:  return VFIcon.recording
        }
    }

    static let allCases: [MainContentSection] = [.home, .dictionary, .knowledge, .recording]
}

// MARK: - Settings Dialog Section (Ayrı dialog nav)

enum SettingsDialogSection: String, Identifiable {
    case general = "Genel"
    case account = "Hesap"
    case about   = "Hakkında"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .general: return "square.grid.2x2"
        case .account: return VFIcon.account
        case .about:   return VFIcon.about
        }
    }

    static let allCases: [SettingsDialogSection] = [.general, .account, .about]
}

// MARK: - SettingsSection (backward compat — eski kod için)

enum SettingsSection: String, Identifiable {
    case general       = "Genel"
    case dictionary    = "Sözlük"
    case knowledgeBase = "Proje Terimleri"
    case recording     = "Kayıt"
    case account       = "Hesap"
    case about         = "Hakkında"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .general:       return "square.grid.2x2"
        case .dictionary:    return VFIcon.dictionary
        case .knowledgeBase: return VFIcon.knowledgeBase
        case .recording:     return VFIcon.recording
        case .account:       return VFIcon.account
        case .about:         return VFIcon.about
        }
    }

    static let mainNav: [SettingsSection]   = [.general, .dictionary, .knowledgeBase, .recording]
    static let bottomNav: [SettingsSection] = [.account, .about]
}

// MARK: - SectionBanner

struct SectionBanner: View {
    let gradient: LinearGradient
    let title: String
    let subtitle: String
    var iconName: String? = nil

    var body: some View {
        ZStack(alignment: .bottomLeading) {
            gradient

            // Subtle noise/texture overlay
            Color.white.opacity(0.04)

            VStack(alignment: .leading, spacing: 4) {
                if let icon = iconName {
                    Image(systemName: icon)
                        .font(.system(size: 22, weight: .semibold))
                        .foregroundStyle(.white.opacity(0.85))
                        .padding(.bottom, 2)
                }
                Text(title)
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(.white)
                Text(subtitle)
                    .font(.system(size: 12))
                    .foregroundStyle(.white.opacity(0.72))
                    .lineLimit(1)
            }
            .padding(.horizontal, 22)
            .padding(.vertical, 18)
        }
        .frame(maxWidth: .infinity)
        .frame(height: VFLayout.sectionBannerHeight)
        .clipShape(RoundedRectangle(cornerRadius: VFRadius.lg))
        .padding(.horizontal, 20)
        .padding(.top, 20)
    }
}

// MARK: - MainContentView (Ana pencere — Home + Feature sections)

struct MainContentView: View {
    let store: StoreOf<AppFeature>
    var onOpenSettings: (() -> Void)? = nil

    @State private var selectedSection: MainContentSection = .home
    @State private var sidebarCollapsed = false
    @AppStorage(AppSettings.userName) private var userName = ""

    var body: some View {
        VStack(spacing: 0) {

            // ── Titlebar row ──────────────────────────────────────────────
            HStack(spacing: 0) {
                Spacer().frame(width: 76)
                Button {
                    withAnimation(VFAnimation.standard) { sidebarCollapsed.toggle() }
                } label: {
                    Image(systemName: sidebarCollapsed ? "sidebar.right" : "sidebar.left")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                .help(sidebarCollapsed ? "Navigasyonu Genişlet" : "Navigasyonu Daralt")

                Spacer()

                // Profile avatar butonu (sağ üst)
                Button {
                    onOpenSettings?()
                } label: {
                    ProfileAvatarView(name: userName)
                }
                .buttonStyle(.plain)
                .help("Profil & Ayarlar")
                .padding(.trailing, 16)
            }
            .frame(height: 44)
            .background(Color(nsColor: .windowBackgroundColor))

            // ── Ana alan ─────────────────────────────────────────────────
            HStack(spacing: 0) {

                // Sidebar
                VStack(alignment: .leading, spacing: 0) {

                    // Logo
                    HStack(spacing: 8) {
                        Image(systemName: VFIcon.appLogo)
                            .font(.system(size: 20, weight: .semibold))
                            .foregroundStyle(.primary)
                        if !sidebarCollapsed {
                            Text("VoiceFlow")
                                .font(.system(size: 17, weight: .bold))
                                .transition(.opacity.combined(with: .move(edge: .leading)))
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: sidebarCollapsed ? .center : .leading)
                    .padding(.horizontal, sidebarCollapsed ? 0 : 20)
                    .padding(.top, 10)
                    .padding(.bottom, 16)

                    // Nav items
                    VStack(spacing: 2) {
                        ForEach(MainContentSection.allCases) { section in
                            MainSidebarItem(
                                label: section.rawValue,
                                icon: section.icon,
                                isSelected: selectedSection == section,
                                collapsed: sidebarCollapsed
                            ) {
                                selectedSection = section
                            }
                        }
                    }
                    .padding(.horizontal, 10)

                    Spacer()

                    Divider().padding(.horizontal, 12).padding(.bottom, 6)

                    // Settings butonu sol altta
                    MainSidebarItem(
                        label: "Ayarlar",
                        icon: "gearshape",
                        isSelected: false,
                        collapsed: sidebarCollapsed
                    ) {
                        onOpenSettings?()
                    }
                    .padding(.horizontal, 10)
                    .padding(.bottom, 14)
                }
                .frame(width: sidebarCollapsed ? VFLayout.sidebarCollapsedWidth : VFLayout.sidebarWidth)
                .background(Color(nsColor: .windowBackgroundColor))
                .animation(VFAnimation.standard, value: sidebarCollapsed)

                // Content
                ScrollView {
                    Group {
                        switch selectedSection {
                        case .home:
                            HomeSection(store: store)
                        case .dictionary:
                            DictionarySection(store: store.scope(state: \.settings, action: \.settings))
                        case .knowledge:
                            KnowledgeBaseSection(store: store.scope(state: \.settings, action: \.settings))
                        case .recording:
                            RecordingSection(store: store.scope(state: \.recording, action: \.recording))
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .topLeading)
                }
                .background(Color(nsColor: .controlBackgroundColor))
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .shadow(color: .black.opacity(0.06), radius: 6, x: 0, y: 2)
                .padding(.trailing, 8)
                .padding(.bottom, 8)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            .background(Color(nsColor: .windowBackgroundColor))
        }
        .frame(minWidth: 700, maxWidth: .infinity, minHeight: 500, maxHeight: .infinity)
        .background(Color(nsColor: .windowBackgroundColor))
        .ignoresSafeArea(.all)
    }
}

// MARK: - SettingsView (backward compat alias — MenuBarController eski çağrılar için)

typealias SettingsView = MainContentView

// MARK: - SettingsDialogView (Ayrı dialog penceresi — Genel, Hesap, Hakkında)

struct SettingsDialogView: View {
    let store: StoreOf<AppFeature>

    @State private var selectedSection: SettingsDialogSection = .general

    var body: some View {
        HStack(spacing: 0) {

            // Sidebar
            VStack(alignment: .leading, spacing: 0) {
                Text("Ayarlar")
                    .font(.system(size: 15, weight: .semibold))
                    .padding(.horizontal, 16)
                    .padding(.top, 20)
                    .padding(.bottom, 12)

                VStack(spacing: 2) {
                    ForEach(SettingsDialogSection.allCases) { section in
                        DialogSidebarItem(
                            label: section.rawValue,
                            icon: section.icon,
                            isSelected: selectedSection == section
                        ) {
                            selectedSection = section
                        }
                    }
                }
                .padding(.horizontal, 8)

                Spacer()
            }
            .frame(width: 190)
            .background(Color(nsColor: .windowBackgroundColor))

            Divider()

            // Content
            ScrollView {
                Group {
                    switch selectedSection {
                    case .general:
                        GeneralSection(store: store.scope(state: \.recording, action: \.recording))
                    case .account:
                        AccountSection(
                            settingsStore: store.scope(state: \.settings, action: \.settings),
                            authStore: store.scope(state: \.auth, action: \.auth)
                        )
                    case .about:
                        AboutSection(store: store.scope(state: \.recording, action: \.recording))
                    }
                }
                .frame(maxWidth: .infinity, alignment: .topLeading)
            }
            .background(Color(nsColor: .controlBackgroundColor))
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(width: 750, height: 550)
        .background(Color(nsColor: .windowBackgroundColor))
    }
}

// MARK: - MainSidebarItem (MainContentView için)

struct MainSidebarItem: View {
    let label: String
    let icon: String
    let isSelected: Bool
    let collapsed: Bool
    let onTap: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 12) {
                Image(systemName: icon)
                    .font(.system(size: 17, weight: .regular))
                    .frame(width: 22, height: 22)
                    .foregroundStyle(isSelected ? Color.primary : Color.secondary)

                if !collapsed {
                    Text(label)
                        .font(.system(size: 15, weight: isSelected ? .medium : .regular))
                        .foregroundStyle(isSelected ? Color.primary : Color.secondary)
                        .transition(.opacity.combined(with: .move(edge: .leading)))
                }
            }
            .frame(maxWidth: .infinity, alignment: collapsed ? .center : .leading)
            .padding(.horizontal, collapsed ? 8 : 14)
            .padding(.vertical, 9)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isSelected
                          ? Color.primary.opacity(0.08)
                          : isHovered ? Color.primary.opacity(0.04) : Color.clear)
            )
        }
        .buttonStyle(.plain)
        .onHover { isHovered = $0 }
        .help(collapsed ? label : "")
    }
}

// MARK: - DialogSidebarItem (SettingsDialogView için)

struct DialogSidebarItem: View {
    let label: String
    let icon: String
    let isSelected: Bool
    let onTap: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 10) {
                Image(systemName: icon)
                    .font(.system(size: 14, weight: .regular))
                    .frame(width: 18, height: 18)
                    .foregroundStyle(isSelected ? Color.primary : Color.secondary)
                Text(label)
                    .font(.system(size: 13, weight: isSelected ? .medium : .regular))
                    .foregroundStyle(isSelected ? Color.primary : Color.secondary)
                Spacer()
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 7)
                    .fill(isSelected
                          ? Color.primary.opacity(0.08)
                          : isHovered ? Color.primary.opacity(0.04) : Color.clear)
            )
        }
        .buttonStyle(.plain)
        .onHover { isHovered = $0 }
    }
}

// MARK: - SidebarNavItem (backward compat — eski kodlar için)

struct SidebarNavItem: View {
    let section: SettingsSection
    let isSelected: Bool
    let collapsed: Bool
    let onTap: () -> Void

    var body: some View {
        MainSidebarItem(
            label: section.rawValue,
            icon: section.icon,
            isSelected: isSelected,
            collapsed: collapsed,
            onTap: onTap
        )
    }
}

// MARK: - Shared Settings UI Components

/// Yuvarlak köşeli kart — section içeriğini sarar.
struct VFCard<Content: View>: View {
    @ViewBuilder var content: () -> Content
    var body: some View {
        VStack(spacing: 0) { content() }
            .background(Color(nsColor: .controlBackgroundColor))
            .clipShape(RoundedRectangle(cornerRadius: VFRadius.lg))
    }
}

/// Section başlığı — bold, birincil renk.
struct VFSectionHeader: View {
    let title: String
    init(_ title: String) { self.title = title }
    var body: some View {
        Text(title)
            .font(.system(size: 13, weight: .semibold))
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, VFSpacing.xs)
    }
}

/// Label + trailing content satırı. Sonuncu satırda `divider: false` ver.
struct VFRow<Trailing: View>: View {
    let label: String
    let divider: Bool
    @ViewBuilder var trailing: () -> Trailing

    init(_ label: String, divider: Bool = true, @ViewBuilder trailing: @escaping () -> Trailing) {
        self.label = label
        self.divider = divider
        self.trailing = trailing
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: VFSpacing.xxl) {
                Text(label).font(VFFont.body)
                Spacer(minLength: VFSpacing.xl)
                trailing()
            }
            .padding(.horizontal, VFSpacing.xxl)
            .padding(.vertical, VFSpacing.xl)
            if divider {
                Divider().padding(.leading, VFSpacing.xxl)
            }
        }
    }
}

/// Info satırı — icon + caption metin. (Eski: VFInfoRow — artık InfoNote kullan)
struct VFInfoRow: View {
    let icon: String
    let text: String
    let color: Color
    var body: some View {
        InfoNote(icon: icon, text: text, color: color)
    }
}

/// Sağ üst köşe — profile ikonu.
struct ProfileAvatarView: View {
    let name: String

    var body: some View {
        Image(systemName: "person.circle")
            .font(.system(size: 20))
            .foregroundStyle(.secondary)
    }
}

/// Yeni settings info satırı — icon + açıklama.
struct InfoNote: View {
    let icon: String
    let text: String
    let color: Color
    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: icon)
                .foregroundStyle(color)
                .font(.system(size: 12))
                .padding(.top, 1)
            Text(text)
                .font(.system(size: 12))
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 4)
    }
}
