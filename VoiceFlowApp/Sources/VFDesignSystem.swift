import SwiftUI
import AppKit

// MARK: - VFColor
// Tek kaynak renk token'ları. Asla bu dosya dışında .blue/.red/Color(...) kullanma.

enum VFColor {

    // MARK: Semantic
    static let primary:     Color = .accentColor
    static let destructive: Color = .red
    static let success:     Color = .green
    static let warning:     Color = .orange

    // MARK: Mode
    static let modeGeneral:     Color = .blue
    static let modeEngineering: Color = .green
    static let modeOffice:      Color = .orange

    static func forMode(_ mode: AppMode) -> Color {
        switch mode {
        case .general:     return modeGeneral
        case .engineering: return modeEngineering
        case .office:      return modeOffice
        }
    }

    // MARK: Pill (Recording overlay)
    static let pillBackground: Color = Color.black.opacity(0.85)
    static let pillForeground: Color = Color.white
    static let pillEye:        Color = Color.white.opacity(0.95)
    static let pillMouth:      Color = Color.white.opacity(0.90)

    // MARK: Accent overlays (pass base color)
    static func fill(_ c: Color)   -> Color { c.opacity(0.18) }
    static func border(_ c: Color) -> Color { c.opacity(0.45) }
    static func track(_ c: Color)  -> Color { c.opacity(0.20) }
    static func arc(_ c: Color)    -> Color { c.opacity(0.70) }
    static func shadow(_ c: Color) -> Color { c.opacity(0.35) }
    static func glow(_ c: Color)   -> Color { c.opacity(0.40) }

    // MARK: Card surfaces
    static let cardOrange: Color = Color.orange.opacity(0.08)
    static let cardGreen:  Color = Color.green.opacity(0.05)
    static let cardBlue:   Color = Color.accentColor.opacity(0.07)
    static let cardLight:  Color = Color.orange.opacity(0.05)

    // MARK: History badges
    static let badgeLLM: Color = .green
    static let badgeRaw: Color = .orange
}

// MARK: - VFFont
// Tipografi token'ları — tüm font referansları buradan.

enum VFFont {

    // Display
    static let termDisplay:  Font = .system(size: 42, weight: .bold,    design: .rounded)
    static let largeIcon:    Font = .system(size: 56)

    // Titles
    static let title:        Font = .title.bold()
    static let title2:       Font = .title2.bold()
    static let title3:       Font = .title3
    static let title3Semibold: Font = .title3.weight(.semibold)

    // Body
    static let headline:     Font = .headline
    static let subheadline:  Font = .subheadline
    static let body:         Font = .body
    static let callout:      Font = .callout
    static let monospaced:   Font = .system(.body, design: .monospaced)

    // Small
    static let caption:      Font = .caption
    static let caption2:     Font = .caption2

    // Special components
    static let badge:        Font = .system(size: 10, weight: .semibold)
    static let badgeMode:    Font = .system(size: 9)
    static let pillIcon:     Font = .system(size: 18, weight: .semibold)
    static let pillText:     Font = .system(size: 17, weight: .semibold, design: .rounded)
    static let countdown:    Font = .system(size: 10, weight: .semibold, design: .rounded)
    static let trainingIcon: Font = .system(size: 14, weight: .semibold)
    static let sentenceBody: Font = .system(size: 18, weight: .medium)
    static let historyItem:  Font = .system(size: 13)
    static let historyRaw:   Font = .system(size: 11)
    static let sidebarLogo:  Font = .title3
}

// MARK: - VFSpacing
// 4pt grid. Değişiklik için yalnızca bu enum'u düzenle.

enum VFSpacing {
    static let xxs:  CGFloat = 2
    static let xs:   CGFloat = 4
    static let sm:   CGFloat = 6
    static let md:   CGFloat = 8
    static let lg:   CGFloat = 10
    static let xl:   CGFloat = 12
    static let xxl:  CGFloat = 16
    static let xxxl: CGFloat = 20
    static let huge: CGFloat = 24
    static let max:  CGFloat = 32
}

// MARK: - VFRadius
// Köşe yarıçapı ölçeği.

enum VFRadius {
    static let xs:   CGFloat = 2    // waveform bar
    static let sm:   CGFloat = 4    // badge
    static let md:   CGFloat = 8    // button, small card, mode row
    static let lg:   CGFloat = 12   // card
    static let xl:   CGFloat = 14   // sentence card
    static let xxl:  CGFloat = 18   // term card
    static let pill: CGFloat = 24   // recording pill
}

// MARK: - VFAnimation
// Tüm animasyon eğrileri ve süreleri.

enum VFAnimation {
    static let blink:     Animation = .easeInOut(duration: 0.07)
    static let wave:      Animation = .easeInOut(duration: 0.10)
    static let bounce:    Animation = .easeInOut(duration: 0.25)
    static let standard:  Animation = .easeInOut(duration: 0.30)
    static let spring:    Animation = .spring(response: 0.30)
    static let countdown: Animation = .linear(duration: 1)
}

// MARK: - VFIcon
// SF Symbol string sabitleri. Uygulama genelinde symbol isimleri buradan.

enum VFIcon {

    // MARK: Settings sidebar navigation
    static let settings:      String = "gearshape"
    static let recording:     String = "mic"
    static let micFill:       String = "mic.fill"
    static let dictionary:    String = "character.book.closed"
    static let snippets:      String = "text.badge.plus"
    static let knowledgeBase: String = "books.vertical"
    static let account:       String = "person.circle"
    static let about:         String = "info.circle"
    static let sidebar:       String = "sidebar.left"

    // MARK: App logo
    static let appLogo:       String = "waveform"
    static let appLogoFill:   String = "waveform.circle.fill"

    // MARK: Modes — outline (menu, settings)
    static let modeGeneral:     String = "text.bubble"
    static let modeEngineering: String = "chevron.left.forwardslash.chevron.right"
    static let modeOffice:      String = "envelope"

    // MARK: Modes — filled (floating indicator)
    static let modeGeneralFilled:     String = "text.bubble.fill"
    static let modeEngineeringFilled: String = "chevron.left.forwardslash.chevron.right"
    static let modeOfficeFilled:      String = "envelope.fill"

    // MARK: Actions
    static let add:          String = "plus"
    static let delete:       String = "trash"
    static let copy:         String = "doc.on.doc"
    static let shareTeam:    String = "person.2.badge.plus"
    static let checkmark:    String = "checkmark"
    static let checkFill:    String = "checkmark.circle.fill"
    static let circle:       String = "circle"
    static let arrow:        String = "arrow.right"
    static let edit:         String = "pencil"
    static let play:         String = "play.circle.fill"
    static let restart:      String = "arrow.clockwise"
    static let restartCircle: String = "arrow.clockwise.circle"

    // MARK: Status
    static let secure:         String = "lock.shield"
    static let secureFill:     String = "lock.shield.fill"
    static let warning:        String = "exclamationmark.triangle"
    static let bolt:           String = "bolt.fill"
    static let accessibility:  String = "accessibility"
}

// MARK: - VFLayout
// Pencere boyutları, overlay boyutları, sidebar genişlikleri.

enum VFLayout {

    enum WindowSize {
        static let settings:   CGSize = CGSize(width: 900, height: 620)
        static let history:    CGSize = CGSize(width: 420, height: 480)
        static let context:    CGSize = CGSize(width: 460, height: 300)
        static let login:      CGSize = CGSize(width: 380, height: 320)
        static let onboarding: CGSize = CGSize(width: 480, height: 360)
        static let itDataset:  CGSize = CGSize(width: 520, height: 600)
    }

    enum Overlay {
        static let pill:          CGSize = CGSize(width: 140, height: 48)
        static let modeIndicator: CGSize = CGSize(width: 220, height: 60)
        static let trainingPill:  CGSize = CGSize(width: 88,  height: 88)
    }

    // Sidebar
    static let sidebarWidth:          CGFloat = 200
    static let sidebarMinWidth:       CGFloat = 190
    static let sidebarCollapsedWidth: CGFloat = 56

    // Input fields
    static let fieldLarge:  CGFloat = 360
    static let fieldMedium: CGFloat = 320
    static let fieldSmall:  CGFloat = 100

    // Screen edge insets
    static let overlayBottomInset: CGFloat = 60
    static let overlayEdgeInset:   CGFloat = 20

    // Component sizes
    static let micButtonSize:      CGFloat = 64
    static let onboardingIconSize: CGFloat = 64
    static let trainingPillSize:   CGFloat = 60

    // Waveform
    static let waveBarCount:     Int     = 6
    static let waveBarWidth:     CGFloat = 4
    static let waveBarMaxHeight: CGFloat = 32
    static let waveBarMinHeight: CGFloat = 8

    // Dots
    static let dotCount:  Int     = 3
    static let dotSize:   CGFloat = 8
    static let dotScale:  CGFloat = 1.7

    // Face eyes
    static let eyeWidth:  CGFloat = 5
    static let eyeHeight: CGFloat = 6
    static let mouthWidth:  CGFloat = 18
    static let mouthHeight: CGFloat = 10
}

// MARK: - AppMode Extensions
// Mode'a özgü tasarım değerleri — Models.swift'e dokunmadan eklendi.

extension AppMode {
    /// Semantic rengi (VFColor'dan).
    var color: Color { VFColor.forMode(self) }

    /// Floating indicator için filled SF Symbol.
    var indicatorIcon: String {
        switch self {
        case .general:     return VFIcon.modeGeneralFilled
        case .engineering: return VFIcon.modeEngineeringFilled
        case .office:      return VFIcon.modeOfficeFilled
        }
    }
}

// MARK: - VFShadow (ViewModifier)
// Glassmorphism kapsülleri için çift gölge — accent + base.

struct VFAccentShadow: ViewModifier {
    let accent: Color
    func body(content: Content) -> some View {
        content
            .shadow(color: VFColor.shadow(accent), radius: 16, x: 0, y: 4)
            .shadow(color: .black.opacity(0.25),   radius:  8, x: 0, y: 2)
    }
}

extension View {
    /// Glassmorphism kapsüller için standart çift gölge.
    func vfAccentShadow(accent: Color) -> some View {
        modifier(VFAccentShadow(accent: accent))
    }

    /// Kayıt düğmesi için dinamik gölge (kırmızı kayıt sırasında, accent normalde).
    func vfMicShadow(isRecording: Bool) -> some View {
        shadow(
            color: VFColor.glow(isRecording ? .red : .accentColor),
            radius: 12
        )
    }
}
