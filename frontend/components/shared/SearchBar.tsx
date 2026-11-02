'use client'

import { useQuery } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { FormEvent, useEffect, useRef, useState } from 'react'
import { X } from 'lucide-react'
import { movieApi } from '@/lib/api'
import { formatReleaseDate } from '@/lib/formatters'

export function SearchBar({ initialValue = '', onNavigate }: { initialValue?: string; onNavigate?: () => void }) {
  const router = useRouter()
  const input = useRef<HTMLInputElement>(null)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [query, setQuery] = useState(initialValue)
  const [deferredQuery, setDeferredQuery] = useState(initialValue.trim())
  const [previousInitial, setPreviousInitial] = useState(initialValue)
  if (previousInitial !== initialValue) {
    setPreviousInitial(initialValue)
    setQuery(initialValue)
    setPreviewOpen(false)
  }
  useEffect(() => {
    const timer = setTimeout(() => setDeferredQuery(query.trim()), 300)
    return () => clearTimeout(timer)
  }, [query])

  const currentTerm = query.trim()
  const synchronized = currentTerm === deferredQuery
  const canPreview = previewOpen && currentTerm.length > 1
  const searchPreviewQuery = useQuery({
    queryKey: ['search-preview', deferredQuery],
    queryFn: ({ signal }) => movieApi.browseCatalog({ q: deferredQuery, sort: 'hype', page: 1, page_size: 6 }, signal),
    enabled: canPreview && synchronized,
    staleTime: 5 * 60 * 1000,
  })
  const previewItems = canPreview && synchronized ? searchPreviewQuery.data?.items || [] : []

  function navigate(url: string) {
    setPreviewOpen(false)
    router.push(url)
    onNavigate?.()
  }
  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (currentTerm) navigate(`/search?q=${encodeURIComponent(currentTerm)}`)
  }

  return (
    <div className="search-shell">
      <form className="search-bar" onSubmit={onSubmit}>
        <input ref={input} aria-label="Search movies" className="search-input"
          onChange={event => { setQuery(event.target.value); setPreviewOpen(true) }}
          onFocus={() => setPreviewOpen(true)}
          onKeyDown={event => { if (event.key === 'Escape') setPreviewOpen(false) }}
          placeholder="Search films, filmmakers, cast or genres" value={query} />
        {query && <button className="search-clear icon-button" type="button" aria-label="Clear search" onClick={() => { setQuery(''); setDeferredQuery(''); input.current?.focus() }}><X size={16}/></button>}
        <button className="cta-button" type="submit">Search</button>
      </form>
      {canPreview && (!synchronized || searchPreviewQuery.isLoading) && <div className="search-suggestions panel" role="status"><p className="subtle">Searching...</p></div>}
      {canPreview && synchronized && searchPreviewQuery.isError ? (
        <div className="search-suggestions panel" role="alert"><p>Search is unavailable. Check your connection and try again.</p><button className="cta-button secondary-button" onClick={() => void searchPreviewQuery.refetch()}>Retry search</button></div>
      ) : previewItems.length ? (
        <div className="search-suggestions panel">
          {previewItems.map(item => <button className="suggestion-row" key={item.id} onClick={() => navigate(`/movies/${item.slug}`)} type="button">
            <span><strong>{item.title}</strong><span className="meta suggestion-supporting-copy">{item.status} • {formatReleaseDate(item.release_date)}</span></span>
            <span className="meta">{item.imdb_rating ? `IMDb ${item.imdb_rating}` : 'Explore ↗'}</span>
          </button>)}
        </div>
      ) : canPreview && synchronized && searchPreviewQuery.isSuccess ? (
        <div className="search-suggestions panel" role="status"><p className="subtle">No quick matches found.</p></div>
      ) : null}
    </div>
  )
}
