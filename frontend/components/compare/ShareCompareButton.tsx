'use client'

import { useState } from 'react'

export function ShareCompareButton({ ids }: { ids: number[] }) {
  const [copied, setCopied] = useState(false)
  const [fallback, setFallback] = useState('')

  async function handleShare() {
    const url = new URL(window.location.href)
    url.searchParams.set('ids', ids.join(','))
    try {
      await navigator.clipboard.writeText(url.toString())
      setCopied(true); setFallback('')
    } catch { setFallback(url.toString()) }
  }

  return (
    <div><button className="cta-button secondary-button" onClick={() => void handleShare()} type="button">
      {copied ? 'Link copied' : 'Share comparison'}
    </button>
      {fallback && <p role="status"><label htmlFor="compare-share-link">Copy this comparison link</label><input id="compare-share-link" className="search-input" readOnly value={fallback} onFocus={event => event.target.select()} /></p>}
    </div>
  )
}
