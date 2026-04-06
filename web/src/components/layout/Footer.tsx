import { Container } from '@/components/ui/Container'

export function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="bg-[var(--page-bg)] border-t border-[var(--divider)]">
      <Container>
        <div className="py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <img
            src="/text_logo.svg"
            alt="VoiceFlow"
            className="h-auto w-28 opacity-30 dark:brightness-0 dark:invert"
          />
          <p className="text-xs text-[var(--subtle)]">
            &copy; {currentYear} VoiceFlow · demo@voiceflow.ai
          </p>
        </div>
      </Container>
    </footer>
  )
}
