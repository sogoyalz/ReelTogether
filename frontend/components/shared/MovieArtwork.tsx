'use client'
import Image from 'next/image'
import { useState } from 'react'
import { Film } from 'lucide-react'

export function MovieArtwork({ src, title, backdrop = false }: { src?: string | null; title: string; backdrop?: boolean }) {
  const [failedSource, setFailedSource] = useState<string | null>(null)
  const [loadedSource, setLoadedSource] = useState<string | null>(null)
  const valid = Boolean(src && /^https?:\/\//.test(src) && src !== failedSource)
  return <div className={backdrop ? 'film-artwork film-artwork-backdrop' : 'film-artwork'}>
    {valid ? <Image className={loadedSource === src ? 'artwork-ready' : 'artwork-loading'} onLoad={() => setLoadedSource(src!)} src={src!} alt="" fill sizes={backdrop ? '100vw' : '(max-width: 600px) 45vw, 300px'} unoptimized onError={() => setFailedSource(src!)} /> : <div className="film-artwork-fallback"><Film size={32} aria-hidden="true" /><span>{title}</span></div>}
  </div>
}
