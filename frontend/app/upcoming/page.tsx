'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'

import { MovieCard } from '@/components/shared/MovieCard'
import { movieApi } from '@/lib/api'

export default function UpcomingPage() {
  const upcomingQuery = useQuery({
    queryKey: ['upcoming-movies', 100],
    queryFn: () => movieApi.getUpcoming(100),
  })

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <span className="eyebrow">Upcoming</span>
        <h1 className="hero-title" style={{ fontSize: 'clamp(2.4rem, 6vw, 4.8rem)' }}>
          Track the full upcoming release slate.
        </h1>
        <p className="hero-copy">
          Every announced or upcoming title in the current mock catalog, with direct
          access to each detail page.
        </p>
        <div className="hero-actions" style={{ marginTop: 22 }}>
          <Link className="cta-button" href="/movies">
            Browse all movies
          </Link>
          <Link className="eyebrow" href="/">
            Back to home
          </Link>
        </div>
      </section>

      <div className="section-header">
        <div>
          <h2>Upcoming and Announced</h2>
          <p>{upcomingQuery.data?.length || 0} titles currently listed.</p>
        </div>
      </div>
      {upcomingQuery.isLoading ? (
        <p className="subtle">Loading upcoming slate...</p>
      ) : (
        <div className="section-grid">
          {upcomingQuery.data?.map((movie) => <MovieCard key={movie.id} movie={movie} />)}
        </div>
      )}
    </main>
  )
}
