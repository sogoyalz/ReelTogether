'use client'

import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { MovieCard } from '@/components/shared/MovieCard'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/QueryState'
import { SearchBar } from '@/components/shared/SearchBar'
import { movieApi } from '@/lib/api'

export function SearchResults() {
  const searchParams = useSearchParams()
  const query = searchParams.get('q') || ''
  const [genreFilter, setGenreFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [franchiseFilter, setFranchiseFilter] = useState('all')
  const [studioFilter, setStudioFilter] = useState('all')
  const [directorFilter, setDirectorFilter] = useState('all')
  const [yearFilter, setYearFilter] = useState('')
  const [minimumRating, setMinimumRating] = useState(0)
  const [sortBy, setSortBy] = useState('hype')
  const [page, setPage] = useState(1)
  const filterKey = JSON.stringify([query, statusFilter, genreFilter, franchiseFilter, studioFilter, directorFilter, yearFilter, minimumRating, sortBy])
  const [previousFilters, setPreviousFilters] = useState(filterKey)
  if (previousFilters !== filterKey) {
    setPreviousFilters(filterKey)
    setPage(1)
  }

  const resultsQuery = useQuery({
    queryKey: ['search', query, statusFilter, genreFilter, franchiseFilter, studioFilter, directorFilter, yearFilter, minimumRating, sortBy, page],
    queryFn: () =>
      movieApi.searchMovies({
        q: query,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        genre: genreFilter !== 'all' ? genreFilter : undefined,
        franchise: franchiseFilter !== 'all' ? franchiseFilter : undefined,
        studio: studioFilter !== 'all' ? studioFilter : undefined,
        director: directorFilter !== 'all' ? directorFilter : undefined,
        year: yearFilter ? Number(yearFilter) : undefined,
        min_rating: minimumRating || undefined,
        sort: sortBy,
        page,
        page_size: 24,
      }),
    enabled: query.trim().length > 0,
  })



  const response = resultsQuery.data
  const results = useMemo(() => response?.items || [], [response?.items])
  const genres = response?.facets.genres || []
  const statuses = response?.facets.statuses || []
  const franchises = response?.facets.franchises || []
  const studios = response?.facets.studios || []
  const directors = response?.facets.directors || []
  const years = response?.facets.years || []
  const researchSnapshot = useMemo(() => {
    if (!results.length) {
      return null
    }
    const totalBuzz = results.reduce((sum, item) => sum + item.buzz_score, 0)
    const totalHype = results.reduce((sum, item) => sum + item.hype_score, 0)
    const totalPopularity = results.reduce((sum, item) => sum + item.tmdb_popularity, 0)
    const topResult = [...results].sort((left, right) => right.hype_score - left.hype_score)[0]
    const strongestBuzz = [...results].sort((left, right) => right.buzz_score - left.buzz_score)[0]
    const franchiseMix = results.reduce<Record<string, number>>((accumulator, item) => {
      const key = item.franchise || 'Standalone'
      accumulator[key] = (accumulator[key] || 0) + 1
      return accumulator
    }, {})
    const topFranchise = Object.entries(franchiseMix).sort((left, right) => right[1] - left[1])[0]

    return {
      averageBuzz: (totalBuzz / results.length).toFixed(1),
      averageHype: (totalHype / results.length).toFixed(1),
      averagePopularity: (totalPopularity / results.length).toFixed(1),
      topResult,
      strongestBuzz,
      topFranchise,
    }
  }, [results])

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
              setStatusFilter('all')
              setGenreFilter('all')
              setFranchiseFilter('all')
              setStudioFilter('all')
              setDirectorFilter('all')
              setYearFilter('')
              setMinimumRating(0)
              setSortBy('hype')
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
          <span className="metric-label">Status</span>
          <select className="compare-select" onChange={(event) => setStatusFilter(event.target.value)} value={statusFilter}>
            <option value="all">All</option>
            {statuses.map((status) => <option key={status} value={status}>{status}</option>)}
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
          <span className="metric-label">Director</span>
          <select className="compare-select" onChange={(event) => setDirectorFilter(event.target.value)} value={directorFilter}>
            <option value="all">All</option>
            {directors.map((director) => <option key={director} value={director}>{director}</option>)}
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
        <label>
          <span className="metric-label">Sort</span>
          <select className="compare-select" onChange={(event) => setSortBy(event.target.value)} value={sortBy}>
            <option value="hype">Hype score</option>
            <option value="none">None</option>
            <option value="buzz">Buzz score</option>
            <option value="popularity">Popularity</option>
            <option value="rating">IMDb rating</option>
            <option value="release">Newest release</option>
            <option value="title">Title</option>
          </select>
        </label>
      </div>

      <div className="section-header">
        <div>
          <h2>Results for &quot;{query}&quot;</h2>
          <p>{response?.total || 0} matches in the tracked catalog.</p>
        </div>
        {response ? <p className="meta">{sortBy === 'none' ? `No manual sort applied. Showing ${results.length} results on this page.` : `Sorted by ${sortBy}. Showing ${results.length} results on this page.`}</p> : null}
      </div>
      {researchSnapshot ? (
        <div className="overview-grid" style={{ marginBottom: 20 }}>
          <div className="metric-card">
            <div className="metric-label">Average Buzz</div>
            <div className="metric-value overview-title">{researchSnapshot.averageBuzz}</div>
            <p className="meta">Average buzz across the current result set.</p>
          </div>
          <div className="metric-card">
            <div className="metric-label">Average Hype</div>
            <div className="metric-value overview-title">{researchSnapshot.averageHype}</div>
            <p className="meta">Average hype across the current result set.</p>
          </div>
          <div className="metric-card">
            <div className="metric-label">Average Popularity</div>
            <div className="metric-value overview-title">{researchSnapshot.averagePopularity}</div>
            <p className="meta">TMDB popularity signal across these matches.</p>
          </div>
          <div className="metric-card">
            <div className="metric-label">Top Result</div>
            <div className="metric-value overview-title">{researchSnapshot.topResult.title}</div>
            <p className="meta">Strongest hype signal in the current search.</p>
          </div>
          <div className="metric-card">
            <div className="metric-label">Strongest Buzz</div>
            <div className="metric-value overview-title">{researchSnapshot.strongestBuzz.title}</div>
            <p className="meta">Leading conversation volume right now.</p>
          </div>
          <div className="metric-card">
            <div className="metric-label">Leading Franchise</div>
            <div className="metric-value overview-title">{researchSnapshot.topFranchise?.[0] || 'Mixed'}</div>
            <p className="meta">{researchSnapshot.topFranchise ? `${researchSnapshot.topFranchise[1]} results` : 'No franchise concentration found.'}</p>
          </div>
        </div>
      ) : null}
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
