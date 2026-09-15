'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Menu, X, Clapperboard } from 'lucide-react'

const navItems = [
  { href: '/', label: 'Home' },
  { href: '/movies', label: 'Library' },
  { href: '/discover', label: 'Discover' },
  { href: '/recommendations', label: 'Movie Match' },
  { href: '/movie-night', label: 'Movie Night' },
  { href: '/upcoming', label: 'Upcoming' },
  { href: '/search', label: 'Search' },
  { href: '/watchlist', label: 'Watchlist' },
]

export function SiteHeader() {
  const pathname = usePathname()
  const [menuOpen, setMenuOpen] = useState(false)

  const [previousPath, setPreviousPath] = useState(pathname)
  if (previousPath !== pathname) {
    setPreviousPath(pathname)
    setMenuOpen(false)
  }

  return (
    <header className="site-header" onKeyDown={event => { if (event.key === 'Escape') { setMenuOpen(false); document.querySelector<HTMLButtonElement>('.nav-toggle')?.focus() } }}>
      <div className="site-header-inner">
        <Link className="brand-mark" href="/">
          <span className="brand-symbol"><Clapperboard size={21} aria-hidden="true" /></span>
          <span>
            <strong>ReelTogether</strong>
            <small>A world of cinema.</small>
          </span>
        </Link>
        <button
          aria-controls="site-nav"
          aria-expanded={menuOpen}
          aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
          className="nav-toggle"
          onClick={() => setMenuOpen((open) => !open)}
          type="button"
        >
          {menuOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
        <nav className={menuOpen ? 'site-nav site-nav-open' : 'site-nav'} id="site-nav">
          {navItems.map((item) => {
            const isActive =
              item.href === '/'
                ? pathname === '/'
                : pathname === item.href || pathname.startsWith(`${item.href}/`)

            return (
              <Link
                aria-current={isActive ? 'page' : undefined}
                className={isActive ? 'nav-link nav-link-active' : 'nav-link'}
                href={item.href}
                key={item.href}
                onClick={() => setMenuOpen(false)}
              >
                {item.label}
              </Link>
            )
          })}
        </nav>
      </div>
    </header>
  )
}
