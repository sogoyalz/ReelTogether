'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Menu, Search, X } from 'lucide-react'

const navItems = [
  { href: '/', label: 'Home' },
  { href: '/movies', label: 'Library' },
  { href: '/discover', label: 'Discover' },
  { href: '/compare', label: 'Compare' },
  { href: '/search', label: 'Search' },
]

export function SiteHeader() {
  const pathname = usePathname()
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    setMenuOpen(false)
  }, [pathname])

  return (
    <header className="site-header">
      <div className="site-header-inner">
        <div className="site-header-primary">
          <Link className="brand-mark" href="/">
            <span className="brand-dot" />
            <span>
              <strong>Movie Pulse</strong>
              <small>Analytics Studio</small>
            </span>
          </Link>
          <div className="header-badge">
            <span className="header-badge-dot" />
            Live catalog
          </div>
        </div>
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
                className={isActive ? 'nav-link nav-link-active' : 'nav-link'}
                href={item.href}
                key={item.href}
                aria-current={isActive ? 'page' : undefined}
              >
                {item.label}
              </Link>
            )
          })}
          <Link className="nav-cta" href="/search">
            <Search size={16} />
            Research
          </Link>
        </nav>
      </div>
    </header>
  )
}
