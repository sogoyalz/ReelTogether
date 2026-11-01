'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Bookmark, Compass, Film, Menu, Search, Users, X } from 'lucide-react'
import { SearchBar } from './SearchBar'
import { useAccount } from '@/lib/account'

const navItems = [{ href:'/movies', label:'Library' },{ href:'/discover', label:'Discover' },{ href:'/recommendations', label:'Movie Match' },{ href:'/movie-night', label:'Movie Night' }]
const quickItems = [{ href:'/movies',label:'Library',icon:Film },{ href:'/discover',label:'Discover',icon:Compass },{ href:'/movie-night',label:'Movie Night',icon:Users },{ href:'/watchlist',label:'Watchlist',icon:Bookmark }]

function openSearch(dialog:HTMLDialogElement|null, trigger?:HTMLButtonElement) { trigger?.focus(); dialog?.showModal(); dialog?.querySelector<HTMLInputElement>('input')?.focus() }

export function SiteHeader() {
  const pathname = usePathname()
  const account = useAccount()
  const [menuOpen,setMenuOpen] = useState(false)
  const [previousPath,setPreviousPath] = useState(pathname)
  const search = useRef<HTMLDialogElement>(null)
  if (previousPath !== pathname) { setPreviousPath(pathname); setMenuOpen(false) }
  const searchPath = useRef(pathname)
  useEffect(() => {
    if (searchPath.current !== pathname) {
      search.current?.close()
      searchPath.current = pathname
    }
  },[pathname])
  useEffect(() => {
    const shortcut = (event:KeyboardEvent) => { if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase()==='k') { event.preventDefault(); openSearch(search.current) } }
    const historyChanged = () => search.current?.close()
    window.addEventListener('keydown',shortcut)
    window.addEventListener('popstate',historyChanged)
    return () => { window.removeEventListener('keydown',shortcut); window.removeEventListener('popstate',historyChanged) }
  },[])
  const active = (href:string) => pathname===href || pathname.startsWith(`${href}/`)
  return <>
    <header className="site-header" onKeyDown={event => { if (event.key==='Escape' && menuOpen) { setMenuOpen(false); document.querySelector<HTMLButtonElement>('.nav-toggle')?.focus() } }}>
      <div className="site-header-inner"><Link className="brand-mark" href="/" title="ReelTogether home"><span className="brand-symbol" aria-hidden="true"><svg width="30" height="30" viewBox="0 0 30 30" fill="none"><rect x="2" y="3" width="17" height="24" rx="5" stroke="currentColor" strokeWidth="2"/><rect x="11" y="3" width="17" height="24" rx="5" stroke="currentColor" strokeWidth="2"/><path d="M15 10v10m-4-5h8" stroke="currentColor" strokeWidth="2"/></svg></span><span className="brand-name">Reel<span>Together</span>{' '}<small>THE GOOD FILM CLUB</small></span></Link>
      <nav className={menuOpen?'site-nav site-nav-open':'site-nav'} id="site-nav" aria-label="Main navigation">{navItems.map(item => <Link key={item.href} href={item.href} aria-current={active(item.href)?'page':undefined} className={active(item.href)?'nav-link nav-link-active':'nav-link'} onClick={()=>setMenuOpen(false)}>{item.label}</Link>)}</nav>
      <div className="header-actions"><button className="search-trigger icon-button" aria-label="Open search — ⌘ K" aria-keyshortcuts="Control+K Meta+K" onClick={event=>openSearch(search.current,event.currentTarget)}><Search size={19}/><kbd aria-hidden="true">⌘ K</kbd></button><Link className="header-watchlist" href="/watchlist"><Bookmark size={16}/><span>Watchlist</span>{account.data && <i aria-label={`Signed in as ${account.data.user.username}`}>{account.data.user.username.slice(0,1).toUpperCase()}</i>}</Link><button aria-controls="site-nav" aria-expanded={menuOpen} aria-label={menuOpen?'Close navigation menu':'Open navigation menu'} className="nav-toggle icon-button" onClick={event=>{event.currentTarget.focus();setMenuOpen(!menuOpen)}}>{menuOpen?<X size={21}/>:<Menu size={21}/>}</button></div>
      </div>
    </header>
    <dialog ref={search} className="search-dialog" aria-labelledby="search-title" onClick={event=>{if(event.target===event.currentTarget){const bounds=event.currentTarget.getBoundingClientRect();if(event.clientX<bounds.left||event.clientX>bounds.right||event.clientY<bounds.top||event.clientY>bounds.bottom)search.current?.close()}}}><div className="search-dialog-top"><span className="eyebrow">FOLLOW A TITLE. FIND A WORLD.</span><button className="icon-button" aria-label="Close search" onClick={()=>search.current?.close()}><X size={20}/></button></div><h2 id="search-title">What’s on your mind?</h2><SearchBar onNavigate={() => search.current?.close()} /><p className="meta">Search films, filmmakers, cast, studios or genres. Press Escape to close.</p></dialog>
    <nav className="mobile-dock" aria-label="Quick navigation">{quickItems.map(({href,label,icon:Icon})=><Link key={href} href={href} aria-current={active(href)?'page':undefined}><Icon size={18}/><span>{label}</span></Link>)}</nav>
  </>
}
