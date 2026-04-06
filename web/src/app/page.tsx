import { Navbar } from '@/components/layout/Navbar'
import { Footer } from '@/components/layout/Footer'
import { HeroSection } from '@/components/sections/HeroSection'
import { ProductSection } from '@/components/sections/ProductSection'
import { ClosingSection } from '@/components/sections/ClosingSection'

export default function Home() {
  return (
    <>
      <Navbar />
      <main>
        <HeroSection />
        <ProductSection />
        <ClosingSection />
      </main>
      <Footer />
    </>
  )
}
