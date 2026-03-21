'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { MovieCard } from '@/components/shared/MovieCard'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/QueryState'
import { movieApi } from '@/lib/api'

export default function MoviesLibraryPage() {
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [genreFilter, setGenreFilter] = useState('all')
  const [franchiseFilter, setFranchiseFilter] = useState('all')
  const [studioFilter, setStudioFilter] = useState('all')
  const [streamingFilter, setStreamingFilter] = useState('all')
  const [releaseYear, setReleaseYear] = useState('')
  const [minimumRating, setMinimumRating] = useState(0)
  const [minimumHype, setMinimumHype] = useState(0)
  const [minimumPopularity, setMinimumPopularity] = useState(0)
  const [sortBy, setSortBy] = useState('hype')
  const [page, setPage] = useState(1)

  const catalogQuery = useQuery({
    queryKey: [
      'browse-catalog',
      query,
      statusFilter,
      genreFilter,
      franchiseFilter,
      studioFilter,
      streamingFilter,
      releaseYear,
      minimumRating,
      minimumHype,
      minimumPopularity,
      sortBy,
      page,
    ],
    queryFn: () =>
      movieApi.browseCatalog({
        q: query || undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        genre: genreFilter !== 'all' ? genreFilter : undefined,
        franchise: franchiseFilter !== 'all' ? franchiseFilter : undefined,
        studio: studioFilter !== 'all' ? studioFilter : undefined,
        streaming: streamingFilter !== 'all' ? streamingFilter : undefined,
        year: releaseYear ? Number(releaseYear) : undefined,
        min_rating: minimumRating || undefined,
        min_hype: minimumHype || undefined,
        min_popularity: minimumPopularity || undefined,
        sort: sortBy,
        page,
        page_size: 24,
      }),
  })

  useEffect(() => {
    setPage(1)
  }, [
    query,
    statusFilter,
    genreFilter,
    franchiseFilter,
    studioFilter,
    streamingFilter,
    releaseYear,
    minimumRating,
    minimumHype,
    minimumPopularity,
    sortBy,
  ])

  const response = catalogQuery.data
  const filteredMovies = response?.items || []
  const facets = response?.facets
  const genres = facets?.genres || []
  const franchises = facets?.franchises || []
  const studios = facets?.studios || []
  const streamingPlatforms = facets?.streaming || []
  const years = facets?.years || []

  function resetFilters() {
    setQuery('')
    setStatusFilter('all')
    setGenreFilter('all')
    setFranchiseFilter('all')
    setStudioFilter('all')
    setStreamingFilter('all')
    setReleaseYear('')
    setMinimumRating(0)
    setMinimumHype(0)
    setMinimumPopularity(0)
    setSortBy('hype')
    setPage(1)
  }

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <span className="eyebrow">Library</span>
        <h1 className="hero-title" style={{ fontSize: 'clamp(2.4rem, 6vw, 4.8rem)' }}>
          Browse the full tracked movie library.
        </h1>
        <p className="hero-copy">
          Search movies by name, rating, year, genre, or franchise universe and narrow the catalog
          like a proper movie explorer.
        </p>
        <div className="hero-actions" style={{ marginTop: 22 }}>
          <Link className="cta-button" href="/upcoming">
            See upcoming only
          </Link>
          <Link className="cta-button secondary-button" href="/discover">
            Open discovery
          </Link>
          <button className="cta-button secondary-button" onClick={resetFilters} type="button">
            Clear filters
          </button>
          <Link className="eyebrow" href="/">
            Back to home
          </Link>
        </div>
      </section>

      <div className="section-header">
        <div>
          <h2>Library Filters</h2>
          <p>Filter by release year, genre, status, score, popularity, and streaming availability.</p>
        </div>
      </div>
      <div className="filter-grid panel">
        <label>
          <span className="metric-label">Search</span>
          <input className="search-input" onChange={(event) => setQuery(event.target.value)} placeholder="Search movies, cast, franchise, studio" value={query} />
        </label>
        <label>
          <span className="metric-label">Status</span>
          <select className="compare-select" onChange={(event) => setStatusFilter(event.target.value)} value={statusFilter}>
            <option value="all">All</option>
            <option value="released">Released</option>
            <option value="upcoming">Upcoming</option>
            <option value="announced">Announced</option>
          </select>
        </label>
        <label>
          <span className="metric-label">Genre</span>
          <select className="compare-select" onChange={(event) => setGenreFilter(event.target.value)} value={genreFilter}>
            <option value="all">All</option>
            {genres.map((genre) => <option key={genre} value={genre}>{genre}</option>)}
          </select>
        </label>
        <label>
          <span className="metric-label">Franchise</span>
          <select className="compare-select" onChange={(event) => setFranchiseFilter(event.target.value)} value={franchiseFilter}>
            <option value="all">All</option>
            {franchises.map((franchise) => <option key={franchise} value={franchise}>{franchise}</option>)}
          </select>
        </label>
        <label>
          <span className="metric-label">Studio</span>
          <select className="compare-select" onChange={(event) => setStudioFilter(event.target.value)} value={studioFilter}>
            <option value="all">All</option>
            {studios.map((studio) => <option key={studio} value={studio}>{studio}</option>)}
          </select>
        </label>
        <label>
          <span className="metric-label">Streaming</span>
          <select className="compare-select" onChange={(event) => setStreamingFilter(event.target.value)} value={streamingFilter}>
            <option value="all">All</option>
            {streamingPlatforms.map((platform) => <option key={platform} value={platform}>{platform}</option>)}
          </select>
        </label>
        <label>
          <span className="metric-label">Release Year</span>
          <select className="compare-select" onChange={(event) => setReleaseYear(event.target.value)} value={releaseYear}>
            <option value="">All</option>
            {years.map((year) => <option key={year} value={year}>{year}</option>)}
          </select>
        </label>
        <label>
          <span className="metric-label">Min IMDb</span>
          <input className="search-input" min={0} max={10} onChange={(event) => setMinimumRating(Number(event.target.value || 0))} step="0.1" type="number" value={minimumRating} />
        </label>
        <label>
          <span className="metric-label">Min Hype</span>
          <input className="search-input" min={0} max={100} onChange={(event) => setMinimumHype(Number(event.target.value || 0))} type="number" value={minimumHype} />
        </label>
        <label>
          <span className="metric-label">Min Popularity</span>
          <input className="search-input" min={0} max={100} onChange={(event) => setMinimumPopularity(Number(event.target.value || 0))} type="number" value={minimumPopularity} />
        </label>
        <label>
          <span className="metric-label">Sort</span>
          <select className="compare-select" onChange={(event) => setSortBy(event.target.value)} value={sortBy}>
            <option value="hype">Hype score</option>
            <option value="rating">IMDb rating</option>
            <option value="popularity">Popularity</option>
            <option value="release">Newest release</option>
          </select>
        </label>
      </div>

      <div className="section-header">
        <div>
          <h2>Matching Movies</h2>
          <p>{response?.total || 0} titles match the current filters.</p>
        </div>
        {response ? (
          <p className="meta">Sorted by {sortBy}. Showing {filteredMovies.length} titles on this page.</p>
        ) : null}
      </div>
      {catalogQuery.isLoading ? <LoadingState title="Loading library" description="Applying filters and building the current movie page." /> : null}
      {catalogQuery.isError ? <ErrorState title="Library unavailable" description="The movie library could not be loaded." /> : null}
      {!catalogQuery.isLoading && !catalogQuery.isError && !filteredMovies.length ? (
        <EmptyState title="No movies matched" description="Try broadening the filters or clearing a few constraints." />
      ) : null}
      {!catalogQuery.isLoading && !catalogQuery.isError && filteredMovies.length ? <div className="section-grid">{filteredMovies.map((movie) => <MovieCard key={movie.id} movie={movie} />)}</div> : null}
      {response ? (
        <div className="hero-actions" style={{ marginTop: 26 }}>
          <button className="cta-button secondary-button" disabled={response.page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))} type="button">
            Previous page
          </button>
          <span className="eyebrow">
            Page {response.page} of {response.total_pages}
          </span>
          <button className="cta-button secondary-button" disabled={response.page >= response.total_pages} onClick={() => setPage((current) => current + 1)} type="button">
            Next page
          </button>
        </div>
      ) : null}
    </main>
  )
}
