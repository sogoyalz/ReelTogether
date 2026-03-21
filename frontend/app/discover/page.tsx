'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'

import { MovieCard } from '@/components/shared/MovieCard'
import { ErrorState, LoadingState } from '@/components/shared/QueryState'
import { movieApi } from '@/lib/api'

export default function DiscoverPage() {
  const dashboardQuery = useQuery({
    queryKey: ['discovery-dashboard'],
    queryFn: movieApi.getDiscoveryDashboard,
  })

  const dashboard = dashboardQuery.data
  const editorialCollections = Object.entries(dashboard?.editorial_collections || {})

  function formatLabel(label: string) {
    return label
      .split('_')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ')
  }

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <span className="eyebrow">Discovery</span>
        <h1 className="hero-title" style={{ fontSize: 'clamp(2.4rem, 6vw, 4.8rem)' }}>
          Explore trends by genre, franchise, and collection.
        </h1>
        <p className="hero-copy">
          Discovery pages turn the catalog into browseable pathways instead of a single flat list.
        </p>
        <div className="hero-actions" style={{ marginTop: 22 }}>
          <Link className="cta-button" href="/movies">
            Browse library
          </Link>
          <Link className="cta-button secondary-button" href="/compare">
            Open compare
          </Link>
        </div>
      </section>

      {dashboardQuery.isLoading ? (
        <LoadingState title="Loading discovery dashboard" description="Building genre, franchise, and editorial discovery paths." />
      ) : null}

      {dashboardQuery.isError ? (
        <ErrorState title="Discovery dashboard unavailable" description="The discovery feed could not be loaded." />
      ) : null}

      <div className="section-header">
        <div>
          <h2>Trending by Genre</h2>
          <p>Highest average hype score among current tracked genres.</p>
        </div>
      </div>
      <div className="compare-grid">
        {dashboard?.trending_by_genre.map((bucket) => (
          <Link className="panel discovery-bucket-card" href={`/genres/${encodeURIComponent(bucket.label)}`} key={bucket.label}>
            <div className="metric-label">{bucket.label}</div>
            <div className="metric-value">{bucket.average_hype_score}</div>
            <p className="meta">{bucket.movie_count} tracked movies</p>
          </Link>
        ))}
      </div>

      <div className="section-header">
        <div>
          <h2>Trending by Franchise</h2>
          <p>Collections that are overperforming across the current catalog.</p>
        </div>
      </div>
      <div className="compare-grid">
        {dashboard?.trending_by_franchise.map((bucket) => (
          <Link className="panel discovery-bucket-card" href={`/franchises/${encodeURIComponent(bucket.label)}`} key={bucket.label}>
            <div className="metric-label">{bucket.label}</div>
            <div className="metric-value">{bucket.average_hype_score}</div>
            <p className="meta">{bucket.movie_count} tracked movies</p>
          </Link>
        ))}
      </div>

      {editorialCollections.map(([label, items]) => (
        <section key={label}>
          <div className="section-header">
            <div>
              <h2>{formatLabel(label)}</h2>
              <p>Editorial-style collection built from the current score model.</p>
            </div>
          </div>
          <div className="section-grid">
            {items.map((movie) => <MovieCard key={movie.id} movie={movie} />)}
          </div>
        </section>
      ))}
    </main>
  )
}
