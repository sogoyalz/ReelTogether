'use client'

import { Search } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { FormEvent, useDeferredValue, useState } from 'react'

import { movieApi } from '@/lib/api'
import { formatReleaseDate } from '@/lib/formatters'

export function SearchBar({ initialValue = '' }: { initialValue?: string }) {
  const router = useRouter()
  const [query, setQuery] = useState(initialValue)
  const deferredQuery = useDeferredValue(query)
  const suggestionsQuery = useQuery({
    queryKey: ['search-suggestions', deferredQuery],
    queryFn: () => movieApi.searchSuggestions(deferredQuery),
    enabled: deferredQuery.trim().length > 1,
    staleTime: 5 * 60 * 1000,
  })

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
          className="search-input"
          placeholder="Search movies, genres, franchises, or people"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <button className="cta-button" type="submit">
          <Search size={18} style={{ marginRight: 8 }} />
          Explore Buzz
        </button>
      </form>
      {suggestionsQuery.isLoading && deferredQuery.trim().length > 1 ? (
        <div className="search-suggestions panel">
          <p className="subtle">Searching the catalog…</p>
        </div>
      ) : null}
      {suggestionsQuery.data?.length ? (
        <div className="search-suggestions panel">
          {suggestionsQuery.data.map((item) => (
            <Link className="suggestion-row" href={`/movies/${item.slug}`} key={item.id}>
              <strong>{item.title}</strong>
              <span className="meta">
                {item.status} • {formatReleaseDate(item.release_date)}
              </span>
            </Link>
          ))}
        </div>
      ) : deferredQuery.trim().length > 1 && !suggestionsQuery.isLoading ? (
        <div className="search-suggestions panel">
          <p className="subtle">No quick matches yet. Press enter to search the full library.</p>
        </div>
      ) : null}
    </div>
  )
}
