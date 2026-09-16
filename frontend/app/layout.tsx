import Link from 'next/link'
import type { Metadata } from 'next'

import { SiteHeader } from '@/components/shared/SiteHeader'

import './globals.css'
import './ui-refresh.css'
import './color-motion.css'
import { Providers } from './providers'

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
    <html lang="en" data-scroll-behavior="smooth">
      <body>
        <Providers>
          <div className="site-frame">
            <a className="skip-link" href="#main-content">Skip to content</a>
            <SiteHeader />
            <div id="main-content" tabIndex={-1} />
            {children}
            <footer className="site-footer">
              <div className="site-footer-inner">
                <div>
                  <p className="footer-title">ReelTogether</p>
                  <p className="meta">Good films. Less scrolling. Your next movie night starts here.</p>
                </div>
                <div className="footer-links">
                  <Link href="/movies">Library</Link>
                  <Link href="/discover">Discover</Link>
                  <Link href="/recommendations">Movie Match</Link>
                  <Link href="/compare">Compare</Link>
                  <Link href="/upcoming">Upcoming</Link>
                  <Link href="/search">Search</Link>
                </div>
              </div>
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  )
}
