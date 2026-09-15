'use client'

import { useQuery } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { FormEvent, useEffect, useState } from 'react'

import { movieApi } from '@/lib/api'
import { formatReleaseDate } from '@/lib/formatters'

export function SearchBar({ initialValue = '' }: { initialValue?: string }) {
  const router = useRouter()
  const [query, setQuery] = useState(initialValue)
  const [deferredQuery, setDeferredQuery] = useState(query)
  const [previousInitial, setPreviousInitial] = useState(initialValue)
  if (previousInitial !== initialValue) {
    setPreviousInitial(initialValue)
    setQuery(initialValue)
  }
  useEffect(() => {
    const timer = setTimeout(() => setDeferredQuery(query), 300)
    return () => clearTimeout(timer)
  }, [query])

  const searchPreviewQuery = useQuery({
    queryKey: ['search-preview', deferredQuery],
    queryFn: () =>
      movieApi.browseCatalog({
        q: deferredQuery,
        sort: 'hype',
        page: 1,
        page_size: 6,
      }),
    enabled: deferredQuery.trim().length > 1,
    staleTime: 5 * 60 * 1000,
  })

  const previewItems = deferredQuery.trim().length > 1 ? searchPreviewQuery.data?.items || [] : []

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nextQuery = query.trim()
    if (!nextQuery) {
      return
    }
    router.push(`/search?q=${encodeURIComponent(nextQuery)}`)
  }

  return (
    <div className="search-shell">
      <form className="search-bar" onSubmit={onSubmit}>
        <input
          aria-label="Search movies"
          className="search-input"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search titles, studios, franchises, directors, cast, or genres"
          value={query}
        />
        <button className="cta-button" type="submit">
          Search
        </button>
      </form>

      {searchPreviewQuery.isLoading && deferredQuery.trim().length > 1 ? (
        <div className="search-suggestions panel">
          <p className="subtle">Searching...</p>
        </div>
      ) : null}

      {previewItems.length ? (
        <div className="search-suggestions panel">
          {previewItems.map((item) => (
            <button
              className="suggestion-row"
              key={item.id}
              onClick={() => router.push(`/movies/${item.slug}`)}
              type="button"
            >
              <span>
                <strong>{item.title}</strong>
                <span className="meta suggestion-supporting-copy">
                  {item.status} • {formatReleaseDate(item.release_date)}
                </span>
              </span>
              <span className="meta">Hype {item.hype_score}</span>
            </button>
          ))}
        </div>
      ) : deferredQuery.trim().length > 1 && !searchPreviewQuery.isLoading ? (
        <div className="search-suggestions panel">
          <p className="subtle">No quick matches found.</p>
        </div>
      ) : null}
    </div>
  )
}
