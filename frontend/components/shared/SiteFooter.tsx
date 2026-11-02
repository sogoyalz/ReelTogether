import Link from 'next/link'
import { ArrowUpRight } from 'lucide-react'

export function SiteFooter() {
  return <footer className="site-footer"><div className="footer-top"><div><span className="eyebrow">THE BEST PART IS WHO YOU WATCH WITH.</span><h2>Make a night <em>of it.</em></h2></div><Link href="/movie-night" className="footer-action" aria-label="Plan your next movie night"><ArrowUpRight size={34}/></Link></div><div className="site-footer-inner"><Link href="/" className="footer-wordmark">ReelTogether<span>✳</span></Link><p className="meta">A home for your next great film.</p><div className="footer-links"><Link href="/movies">Library</Link><Link href="/upcoming">Upcoming</Link><Link href="/compare">Compare films</Link><Link href="/account-security">Account security</Link><Link href="/about">About &amp; sources</Link></div></div><div className="footer-bottom"><span>GOOD FILMS. REAL CONNECTIONS.</span><span>DISCOVER · SAVE · CHOOSE TOGETHER</span></div></footer>
}
