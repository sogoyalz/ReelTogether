'use client'
import Image from 'next/image'
import { useState } from 'react'
import { Film } from 'lucide-react'

export function MovieArtwork({ src, title, backdrop = false, priority = false }: { src?: string | null; title: string; backdrop?: boolean; priority?: boolean }) {
  const [failedSource, setFailedSource] = useState<string | null>(null)
  const [loadedSource, setLoadedSource] = useState<string | null>(null)
  const valid = Boolean(src && /^https?:\/\//.test(src) && src !== failedSource)
  const optimized = Boolean(src && (src.startsWith('https://image.tmdb.org/t/p/') || src.startsWith('https://images.unsplash.com/')))
  return <div className={backdrop ? 'film-artwork film-artwork-backdrop' : 'film-artwork'}>
    {valid ? <Image className={loadedSource === src ? 'artwork-ready' : 'artwork-loading'} onLoad={() => setLoadedSource(src!)} src={src!} alt="" fill sizes={backdrop ? '100vw' : '(max-width: 600px) 45vw, 300px'} unoptimized={!optimized} loading={priority ? 'eager' : 'lazy'} fetchPriority={priority ? 'high' : 'auto'} onError={() => setFailedSource(src!)} /> : <div className="film-artwork-fallback" aria-hidden={backdrop || undefined}>{!backdrop && <><Film size={32} aria-hidden="true" /><span>{title}</span></>}</div>}
  </div>
}
