'use client'

import { useState } from 'react'

export function ShareCompareButton({ ids }: { ids: number[] }) {
  const [copied, setCopied] = useState(false)
  const [fallback, setFallback] = useState('')
  const [sharedIds, setSharedIds] = useState<string | null>(null)
  const selection = ids.join(',')
  const currentShare = sharedIds === selection

  async function handleShare() {
    const url = new URL(window.location.href)
    url.searchParams.set('ids', selection)
    try {
      await navigator.clipboard.writeText(url.toString())
      setCopied(true); setFallback('')
    } catch { setCopied(false); setFallback(url.toString()) }
    finally { setSharedIds(selection) }
  }

  return (
    <div><button className="cta-button secondary-button" onClick={() => void handleShare()} type="button">
      {currentShare && copied ? 'Link copied' : 'Share comparison'}
    </button>
      {currentShare && fallback && <p role="status"><label htmlFor="compare-share-link">Copy this comparison link</label><input id="compare-share-link" className="search-input" readOnly value={fallback} onFocus={event => event.target.select()} /></p>}
    </div>
  )
}
