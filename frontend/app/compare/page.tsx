'use client'

import { Suspense, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'

import { ComparisonChart } from '@/components/compare/ComparisonChart'
import { ComparisonSpotlight } from '@/components/compare/ComparisonSpotlight'
import { ComparisonTable } from '@/components/compare/ComparisonTable'
import { ShareCompareButton } from '@/components/compare/ShareCompareButton'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/QueryState'
import { movieApi } from '@/lib/api'

export default function ComparePage() {
  return (
    <Suspense fallback={<main className="page-shell"><p className="subtle">Loading comparison workspace...</p></main>}>
      <CompareWorkspace />
    </Suspense>
  )
}

function CompareWorkspace() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const initialIds = parseSelectedIds(searchParams.get('ids'))
  const [selectedIds, setSelectedIds] = useState<number[]>(initialIds)
  const [pickerQuery, setPickerQuery] = useState('')
  const [pickerPage, setPickerPage] = useState(1)

  const moviesQuery = useQuery({
    queryKey: ['compare-catalog', pickerQuery, pickerPage],
    queryFn: () =>
      movieApi.browseCatalog({
        q: pickerQuery || undefined,
        sort: 'hype',
        page: pickerPage,
        page_size: 48,
      }),
  })

  const comparisonQuery = useQuery({
    queryKey: ['comparison', selectedIds],
    queryFn: () => movieApi.compareMovies(selectedIds),
    enabled: selectedIds.length > 1,
  })

  const selectedSet = new Set(selectedIds)
  const filteredCatalog = useMemo(() => {
    return moviesQuery.data?.items || []
  }, [moviesQuery.data])

  useEffect(() => {
    if (selectedIds.length >= 2 || !moviesQuery.data?.items.length) {
      return
    }
    setSelectedIds(moviesQuery.data.items.slice(0, 2).map((movie) => movie.id))
  }, [moviesQuery.data, selectedIds.length])

  useEffect(() => {
    if (selectedIds.length < 2) {
      return
    }
    const params = new URLSearchParams(searchParams.toString())
    params.set('ids', selectedIds.join(','))
    router.replace(`/compare?${params.toString()}`)
  }, [router, searchParams, selectedIds])

  useEffect(() => {
    setPickerPage(1)
  }, [pickerQuery])

  function toggleId(movieId: number) {
    setSelectedIds((current) => {
      if (current.includes(movieId)) {
        return current.length > 2 ? current.filter((id) => id !== movieId) : current
      }
      return [...current, movieId].slice(0, 4)
    })
  }

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <span className="eyebrow">Comparison Tool</span>
        <h1 className="hero-title" style={{ fontSize: 'clamp(2.4rem, 6vw, 4.6rem)' }}>
          Put movie hype head to head.
        </h1>
        <p className="hero-copy">
          Compare up to four movies across buzz, hype score, trailer reach, social
          mentions, and projected opening weekend performance.
        </p>
        <div className="hero-actions" style={{ marginTop: 22 }}>
          <ShareCompareButton ids={selectedIds} />
          <Link className="eyebrow" href="/movies">
            Browse library
          </Link>
        </div>
        <div style={{ marginTop: 22 }}>
          <input
            className="search-input"
            onChange={(event) => setPickerQuery(event.target.value)}
            placeholder="Filter compare picker by title, franchise, or studio"
            value={pickerQuery}
          />
        </div>
        <div className="compare-picker" style={{ marginTop: 24 }}>
          {filteredCatalog.map((movie) => (
            <button
              className="cta-button"
              key={movie.id}
              onClick={() => toggleId(movie.id)}
              style={{
                opacity: selectedSet.has(movie.id) ? 1 : 0.55,
                background: selectedSet.has(movie.id)
                  ? 'linear-gradient(135deg, #f2f2f2, #9a9a9a)'
                  : 'rgba(255,255,255,0.08)',
              }}
              type="button"
            >
              {movie.title}
            </button>
          ))}
        </div>
        {moviesQuery.data ? (
          <div className="hero-actions" style={{ marginTop: 18 }}>
            <button className="cta-button secondary-button" disabled={moviesQuery.data.page <= 1} onClick={() => setPickerPage((current) => Math.max(1, current - 1))} type="button">
              Previous titles
            </button>
            <span className="eyebrow">
              Picker page {moviesQuery.data.page} of {moviesQuery.data.total_pages}
            </span>
            <button className="cta-button secondary-button" disabled={moviesQuery.data.page >= moviesQuery.data.total_pages} onClick={() => setPickerPage((current) => current + 1)} type="button">
              More titles
            </button>
          </div>
        ) : null}
      </section>

      {moviesQuery.isLoading ? <LoadingState title="Loading compare catalog" description="Preparing movies for the compare workspace." /> : null}
      {moviesQuery.isError ? <ErrorState title="Compare catalog unavailable" description="The compare picker could not be loaded." /> : null}
      {comparisonQuery.isLoading ? <LoadingState title="Building comparison" description="Calculating the head-to-head view for the selected movies." /> : null}
      {comparisonQuery.isError ? <ErrorState title="Comparison unavailable" description="The selected movies could not be compared right now." /> : null}
      {comparisonQuery.data ? (
        <div className="stack" style={{ marginTop: 30 }}>
          <ComparisonSpotlight items={comparisonQuery.data.items} />
          <ComparisonChart items={comparisonQuery.data.items} />
          <ComparisonTable items={comparisonQuery.data.items} />
        </div>
      ) : (
        <EmptyState title="Pick at least two movies" description="Use the compare picker above to build a side-by-side movie view." />
      )}
    </main>
  )
}

function parseSelectedIds(raw: string | null) {
  if (!raw) {
    return []
  }

  return raw
    .split(',')
    .map((value) => Number(value.trim()))
    .filter((value) => Number.isInteger(value) && value > 0)
    .slice(0, 4)
}
