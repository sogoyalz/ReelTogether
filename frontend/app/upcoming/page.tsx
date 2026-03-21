'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'

import { MovieCard } from '@/components/shared/MovieCard'
import { ErrorState, LoadingState } from '@/components/shared/QueryState'
import { movieApi } from '@/lib/api'

export default function UpcomingPage() {
  const upcomingQuery = useQuery({
    queryKey: ['upcoming-movies'],
    queryFn: () =>
      movieApi.browseCatalog({
        status: 'future',
        sort: 'release',
        page: 1,
        page_size: 48,
      }),
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
          <p>{upcomingQuery.data?.total || 0} titles currently listed.</p>
        </div>
      </div>
      {upcomingQuery.isLoading ? <LoadingState title="Loading upcoming slate" description="Pulling the next release wave from the catalog." /> : null}
      {upcomingQuery.isError ? <ErrorState title="Upcoming page unavailable" description="The upcoming movie page could not be loaded." /> : null}
      {upcomingQuery.data ? (
        <div className="section-grid">
          {upcomingQuery.data.items.map((movie) => <MovieCard key={movie.id} movie={movie} />)}
        </div>
      ) : null}
    </main>
  )
}
