'use client'

import Link from 'next/link'
import { useState } from 'react'
import { Pagination } from '@/components/shared/Pagination'
import { useQuery } from '@tanstack/react-query'

import { MovieCard } from '@/components/shared/MovieCard'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/QueryState'
import { movieApi } from '@/lib/api'

export function EntityMovieGrid({
  title,
  eyebrow,
  description,
  browseParams,
}: {
  title: string
  eyebrow: string
  description: string
  browseParams: Record<string, string | number | undefined>
}) {
  const [page, setPage] = useState(1)
  const catalogQuery = useQuery({
    queryKey: ['entity-grid', title, JSON.stringify(browseParams), page],
    queryFn: () => movieApi.browseCatalog({ ...browseParams, page, page_size: 48, sort: 'hype' }),
  })

  const items = catalogQuery.data?.items || []

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
          <p>{catalogQuery.data?.total || 0} matching movies in the current catalog.</p>
        </div>
      </div>
      {catalogQuery.isLoading ? <LoadingState title="Loading matching titles" description="Building the entity page from the movie catalog." /> : null}
      {catalogQuery.isError ? <ErrorState title="Entity page unavailable" description="The matching movie grid could not be loaded." /> : null}
      {!catalogQuery.isLoading && !catalogQuery.isError && !items.length ? (
        <EmptyState title="No matching titles" description="No movies in the current catalog matched this entity page yet." />
      ) : null}
      {!catalogQuery.isLoading && !catalogQuery.isError && items.length ? <div className="section-grid">{items.map((movie) => <MovieCard key={movie.id} movie={movie} />)}</div> : null}
      <Pagination page={catalogQuery.data?.page || page} totalPages={catalogQuery.data?.total_pages || 1} onChange={setPage} />
    </main>
  )
}
