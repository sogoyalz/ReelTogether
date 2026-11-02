import type { Metadata } from 'next'
import localFont from 'next/font/local'
import { SiteFooter } from '@/components/shared/SiteFooter'

import { SiteHeader } from '@/components/shared/SiteHeader'

import './globals.css'
import { Providers } from './providers'

const bodyFont = localFont({ src:'../public/fonts/manrope-variable.woff2', variable:'--font-sans', display:'swap', weight:'200 800', adjustFontFallback:'Arial' })
const displayFont = localFont({ src:'../public/fonts/bodoni-moda-variable.woff2', variable:'--font-display', display:'swap', weight:'400 900', preload:false, adjustFontFallback:'Times New Roman' })

export const metadata: Metadata = {
  title: 'ReelTogether',
  description: 'Discover films, save your watchlist, and choose what to watch together.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${bodyFont.variable} ${displayFont.variable}`} data-scroll-behavior="smooth">
      <body>
        <Providers>
          <div className="site-frame">
            <a className="skip-link" href="#main-content">Skip to content</a>
            <SiteHeader />
            <div id="main-content" tabIndex={-1} />
            {children}
            <SiteFooter />
          </div>
        </Providers>
      </body>
    </html>
  )
}
