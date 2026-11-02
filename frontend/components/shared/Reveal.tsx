'use client'
import { useEffect, useRef } from 'react'

/** Content is visible without JavaScript. Only offscreen content is revealed. */
export function Reveal({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const node = ref.current
    if (!node || !('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    if (node.getBoundingClientRect().top < window.innerHeight) return
    node.dataset.pending = 'true'
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) { delete node.dataset.pending; observer.disconnect() }
    }, { rootMargin: '0px 0px -30px 0px', threshold: 0.04 })
    observer.observe(node)
    return () => { observer.disconnect(); delete node.dataset.pending }
  }, [])
  return <div ref={ref} className={`reveal ${className}`}>{children}</div>
}
