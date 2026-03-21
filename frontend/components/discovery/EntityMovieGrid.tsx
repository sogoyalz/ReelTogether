'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'

import { MovieCard } from '@/components/shared/MovieCard'
import type { MovieSummary } from '@/lib/api'
import { movieApi } from '@/lib/api'

export function EntityMovieGrid({
  title,
  eyebrow,
  description,
  matcher,
}: {
  title: string
  eyebrow: string
  description: string
  matcher: (movie: MovieSummary) => boolean
}) {
  const catalogQuery = useQuery({
    queryKey: ['catalog', 100],
    queryFn: () => movieApi.getCatalog(100),
  })

  const items = (catalogQuery.data || []).filter(matcher)

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <span className="eyebrow">{eyebrow}</span>
        <h1 className="hero-title" style={{ fontSize: 'clamp(2.3rem, 6vw, 4.5rem)' }}>
          {title}
        </h1>
        <p className="hero-copy">{description}</p>
        <div className="hero-actions" style={{ marginTop: 22 }}>
          <Link className="cta-button" href="/discover">
            Explore discovery
          </Link>
          <Link className="eyebrow" href="/movies">
            Back to library
          </Link>
        </div>
      </section>
      <div className="section-header">
        <div>
          <h2>Tracked Titles</h2>
          <p>{items.length} matching movies in the current catalog.</p>
        </div>
      </div>
      {catalogQuery.isLoading ? <p className="subtle">Loading matching titles...</p> : <div className="section-grid">{items.map((movie) => <MovieCard key={movie.id} movie={movie} />)}</div>}
    </main>
  )
}
