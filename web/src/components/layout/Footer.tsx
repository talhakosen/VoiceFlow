import { Container } from '@/components/ui/Container'

export function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="bg-[var(--page-bg)] border-t border-[var(--divider)]">
      <Container>
        <div className="py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 opacity-40">
            <img src="/app-icon.png" alt="" className="h-6 w-6" />
            <span className="font-bold text-sm tracking-tight text-[var(--heading)]">VoiceFlow</span>
          </div>
          <p className="text-xs text-[var(--subtle)]">
            &copy; {currentYear} VoiceFlow · demo@voiceflow.ai
          </p>
        </div>
      </Container>
    </footer>
  )
}
