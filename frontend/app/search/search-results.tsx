'use client'

import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { MovieCard } from '@/components/shared/MovieCard'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/QueryState'
import { SearchBar } from '@/components/shared/SearchBar'
import { movieApi } from '@/lib/api'

export function SearchResults() {
  const searchParams = useSearchParams()
  const query = searchParams.get('q') || ''
  const [genreFilter, setGenreFilter] = useState('all')
  const [franchiseFilter, setFranchiseFilter] = useState('all')
  const [studioFilter, setStudioFilter] = useState('all')
  const [yearFilter, setYearFilter] = useState('')
  const [minimumRating, setMinimumRating] = useState(0)
  const [page, setPage] = useState(1)

  const resultsQuery = useQuery({
    queryKey: ['search', query, genreFilter, franchiseFilter, studioFilter, yearFilter, minimumRating, page],
    queryFn: () =>
      movieApi.searchMovies({
        q: query,
        genre: genreFilter !== 'all' ? genreFilter : undefined,
        franchise: franchiseFilter !== 'all' ? franchiseFilter : undefined,
        studio: studioFilter !== 'all' ? studioFilter : undefined,
        year: yearFilter ? Number(yearFilter) : undefined,
        min_rating: minimumRating || undefined,
        page,
        page_size: 24,
      }),
    enabled: query.trim().length > 0,
  })

  useEffect(() => {
    setPage(1)
  }, [query, genreFilter, franchiseFilter, studioFilter, yearFilter, minimumRating])

  const response = resultsQuery.data
  const results = response?.items || []
  const genres = response?.facets.genres || []
  const franchises = response?.facets.franchises || []
  const studios = response?.facets.studios || []
  const years = response?.facets.years || []

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <span className="eyebrow">Search</span>
        <h1 className="hero-title" style={{ fontSize: 'clamp(2.4rem, 6vw, 4.6rem)' }}>
          Explore the movie conversation.
        </h1>
        <p className="hero-copy">
          Search by title, franchise, studio, cast, or genre, then narrow results by year, brand, and rating.
        </p>
        <div style={{ marginTop: 22 }}>
          <SearchBar initialValue={query} />
        </div>
        <div className="hero-actions" style={{ marginTop: 22 }}>
          <Link className="cta-button secondary-button" href="/movies">
            Open movie explorer
          </Link>
          <button
            className="cta-button secondary-button"
            onClick={() => {
              setGenreFilter('all')
              setFranchiseFilter('all')
              setStudioFilter('all')
              setYearFilter('')
              setMinimumRating(0)
              setPage(1)
            }}
            type="button"
          >
            Reset filters
          </button>
        </div>
      </section>

      <div className="filter-grid panel">
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
          <span className="metric-label">Year</span>
          <select className="compare-select" onChange={(event) => setYearFilter(event.target.value)} value={yearFilter}>
            <option value="">All</option>
            {years.map((year) => <option key={year} value={year}>{year}</option>)}
          </select>
        </label>
        <label>
          <span className="metric-label">Min IMDb</span>
          <input className="search-input" min={0} max={10} onChange={(event) => setMinimumRating(Number(event.target.value || 0))} step="0.1" type="number" value={minimumRating} />
        </label>
      </div>

      <div className="section-header">
        <div>
          <h2>Results for "{query}"</h2>
          <p>{response?.total || 0} matches in the tracked catalog.</p>
        </div>
      </div>
      {resultsQuery.isLoading ? <LoadingState title="Searching movies" description="Scanning the catalog for matching titles and metadata." /> : null}
      {resultsQuery.isError ? <ErrorState title="Search unavailable" description="The search result set could not be loaded." /> : null}
      {!resultsQuery.isLoading && !resultsQuery.isError && !results.length ? (
        <EmptyState title="No search results" description="Try a broader title, franchise, or studio search." />
      ) : null}
      {!resultsQuery.isLoading && !resultsQuery.isError && results.length ? (
        <div className="section-grid">
          {results.map((movie) => <MovieCard key={movie.id} movie={movie} />)}
        </div>
      ) : null}
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
