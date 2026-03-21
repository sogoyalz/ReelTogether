'use client'

import { useState } from 'react'

export function ShareCompareButton({ ids }: { ids: number[] }) {
  const [copied, setCopied] = useState(false)

  async function handleShare() {
    const url = new URL(window.location.href)
    url.searchParams.set('ids', ids.join(','))
    await navigator.clipboard.writeText(url.toString())
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }

  return (
    <button className="cta-button secondary-button" onClick={() => void handleShare()} type="button">
      {copied ? 'Link copied' : 'Share comparison'}
    </button>
  )
}
