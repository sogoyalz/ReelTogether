import Link from 'next/link'
import type { Metadata } from 'next'

import './globals.css'
import { Providers } from './providers'

export const metadata: Metadata = {
  title: 'Movie Pulse',
  description: 'Track movie buzz, compare hype, and explore audience momentum across platforms.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="site-frame">
            <header className="site-header">
              <div className="site-header-inner">
                <Link className="brand-mark" href="/">
                  <span className="brand-dot" />
                  <span>
                    <strong>Movie Pulse</strong>
                    <small>Analytics Studio</small>
                  </span>
                </Link>
                <nav className="site-nav">
                  <Link href="/">Home</Link>
                  <Link href="/movies">Library</Link>
                  <Link href="/discover">Discover</Link>
                  <Link href="/compare">Compare</Link>
                </nav>
              </div>
            </header>
            {children}
            <footer className="site-footer">
              <div className="site-footer-inner">
                <div>
                  <p className="footer-title">Movie Pulse</p>
                  <p className="meta">Cinematic discovery, comparison, and hype tracking in one place.</p>
                </div>
                <div className="footer-links">
                  <Link href="/movies">Library</Link>
                  <Link href="/discover">Discover</Link>
                  <Link href="/compare">Compare</Link>
                </div>
              </div>
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  )
}
