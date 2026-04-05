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

// MARK: - Settings Section

enum SettingsSection: String, CaseIterable, Identifiable {
    case general       = "Genel"
    case recording     = "Kayıt"
    case dictionary    = "Sözlük"
    case snippets      = "Şablonlar"
    case knowledgeBase = "Bilgi Tabanı"
    case account       = "Hesap"
    case about         = "Hakkında"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .general:       return VFIcon.settings
        case .recording:     return VFIcon.recording
        case .dictionary:    return VFIcon.dictionary
        case .snippets:      return VFIcon.snippets
        case .knowledgeBase: return VFIcon.knowledgeBase
        case .account:       return VFIcon.account
        case .about:         return VFIcon.about
        }
    }
}

// MARK: - SettingsView (custom 2-panel — icon strip on collapse)

struct SettingsView: View {
    let store: StoreOf<AppFeature>

    @State private var selectedSection: SettingsSection = .general
    @State private var sidebarCollapsed = false

    // Traffic lights macOS'ta ~x:12, genişlik ~52pt. Collapse butonu hemen sağında.
    private let trafficLightsWidth: CGFloat = 72
    private let toolbarHeight: CGFloat = 44

    var body: some View {
        VStack(spacing: 0) {

            // MARK: Toolbar row — tüm genişlik, sidebar ile aynı arka plan
            HStack(alignment: .center, spacing: 0) {
                Spacer().frame(width: trafficLightsWidth)
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

                Button { selectedSection = .account } label: {
                    Image(systemName: "person.circle")
                        .font(.system(size: 15))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                .help("Hesap")
                .padding(.trailing, 16)
            }
            .padding(.top, 8)
            .padding(.bottom, 8)
            .background(Color(nsColor: .windowBackgroundColor))

            // MARK: Ana alan
            HStack(spacing: 0) {

                // Sidebar
                VStack(alignment: .leading, spacing: 0) {
                    // Logo header — toolbar'ın hemen altında
                    HStack(spacing: 8) {
                        Image(systemName: VFIcon.appLogo)
                            .font(.system(size: 18, weight: .semibold))
                        if !sidebarCollapsed {
                            Text("VoiceFlow")
                                .font(.system(size: 16, weight: .bold))
                                .transition(.opacity.combined(with: .move(edge: .leading)))
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: sidebarCollapsed ? .center : .leading)
                    .padding(.horizontal, sidebarCollapsed ? 0 : 20)
                    .padding(.vertical, 16)

                    // Nav items
                    VStack(spacing: 2) {
                        ForEach(SettingsSection.allCases) { section in
                            SidebarNavItem(
                                section: section,
                                isSelected: selectedSection == section,
                                collapsed: sidebarCollapsed
                            ) { selectedSection = section }
                        }
                    }
                    .padding(.horizontal, 10)

                    Spacer()
                }
                .frame(width: sidebarCollapsed ? VFLayout.sidebarCollapsedWidth : VFLayout.sidebarWidth)
                .background(Color(nsColor: .windowBackgroundColor))
                .animation(VFAnimation.standard, value: sidebarCollapsed)

                // Content card
                ScrollView {
                    Group {
                        switch selectedSection {
                        case .general:
                            GeneralSection(store: store.scope(state: \.recording, action: \.recording))
                        case .recording:
                            RecordingSection(store: store.scope(state: \.recording, action: \.recording))
                        case .dictionary:
                            DictionarySection(store: store.scope(state: \.settings, action: \.settings))
                        case .snippets:
                            SnippetsSection(store: store.scope(state: \.settings, action: \.settings))
                        case .knowledgeBase:
                            KnowledgeBaseSection(store: store.scope(state: \.settings, action: \.settings))
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
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .shadow(color: .black.opacity(0.06), radius: 6, x: 0, y: 2)
                .padding(.trailing, 8)
                .padding(.bottom, 8)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            .background(Color(nsColor: .windowBackgroundColor))
        }
        .frame(width: VFLayout.WindowSize.settings.width, height: VFLayout.WindowSize.settings.height)
        .background(Color(nsColor: .windowBackgroundColor))
        .ignoresSafeArea(.all)
    }
}

// MARK: - SidebarNavItem

struct SidebarNavItem: View {
    let section: SettingsSection
    let isSelected: Bool
    let collapsed: Bool
    let onTap: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 12) {
                Image(systemName: section.icon)
                    .font(.system(size: 18, weight: .regular))
                    .frame(width: 22, height: 22)
                    .foregroundStyle(isSelected ? Color.primary : Color.secondary)

                if !collapsed {
                    Text(section.rawValue)
                        .font(.system(size: 15, weight: isSelected ? .semibold : .regular))
                        .foregroundStyle(isSelected ? Color.primary : Color.secondary)
                        .transition(.opacity.combined(with: .move(edge: .leading)))
                }
            }
            .frame(maxWidth: .infinity, alignment: collapsed ? .center : .leading)
            .padding(.horizontal, collapsed ? 8 : 12)
            .padding(.vertical, 10)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isSelected
                          ? Color.primary.opacity(0.10)
                          : isHovered ? Color.primary.opacity(0.05) : Color.clear)
            )
        }
        .buttonStyle(.plain)
        .onHover { isHovered = $0 }
        .help(collapsed ? section.rawValue : "")
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

/// Info satırı — icon + caption metin.
struct VFInfoRow: View {
    let icon: String
    let text: String
    let color: Color
    var body: some View {
        HStack(spacing: VFSpacing.sm) {
            Image(systemName: icon).foregroundStyle(color)
            Text(text).font(VFFont.caption).foregroundStyle(.secondary)
        }
        .padding(.horizontal, VFSpacing.xs)
    }
}
