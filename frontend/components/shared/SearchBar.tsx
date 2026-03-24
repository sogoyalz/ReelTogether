'use client'

import { Building2, Clapperboard, Search, Sparkles, Users, X, type LucideIcon } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { FormEvent, ReactNode, useDeferredValue, useMemo, useState } from 'react'

import { MovieSummary, movieApi } from '@/lib/api'
import { formatReleaseDate } from '@/lib/formatters'

export function SearchBar({ initialValue = '' }: { initialValue?: string }) {
  const router = useRouter()
  const [query, setQuery] = useState(initialValue)
  const deferredQuery = useDeferredValue(query)
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
  const entityPreview = useMemo(() => buildEntityPreview(previewItems), [previewItems])
  const capabilityActions = useMemo(
    () => buildCapabilityActions({ query, previewItems, entityPreview }),
    [entityPreview, previewItems, query],
  )

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
      <form className="search-bar search-bar-premium" onSubmit={onSubmit}>
        <div className="search-input-shell">
          <div className="search-input-chrome">
            <div className="search-icon-wrap">
              <Search size={18} />
            </div>
            <div className="search-input-copy">
              <span className="search-kicker">Live full-stack search</span>
              <input
                className="search-input search-input-premium"
                placeholder="Search titles, studios, franchises, directors, cast, or genres"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
            </div>
            {query ? (
              <button
                aria-label="Clear search"
                className="search-clear-button"
                onClick={() => setQuery('')}
                type="button"
              >
                <X size={16} />
              </button>
            ) : null}
          </div>
          <div className="search-capability-row">
            {capabilityActions.map((action) => (
              <button
                className="search-capability-pill"
                key={action.label}
                onClick={() => {
                  if (action.mode === 'query') {
                    setQuery(action.href)
                    return
                  }
                  router.push(action.href)
                }}
                type="button"
              >
                <action.icon size={14} />
                <span>{action.label}</span>
                <span className="search-capability-hint">{action.hint}</span>
              </button>
            ))}
          </div>
        </div>
        <button className="cta-button search-submit-button" type="submit">
          <Search size={18} style={{ marginRight: 8 }} />
          Run Research
        </button>
      </form>
      {searchPreviewQuery.isLoading && deferredQuery.trim().length > 1 ? (
        <div className="search-suggestions panel premium-search-suggestions">
          <p className="subtle">Searching titles, studios, franchises, and talent…</p>
        </div>
      ) : null}
      {previewItems.length ? (
        <div className="search-suggestions panel premium-search-suggestions">
          <div className="search-preview-header">
            <div>
              <p className="search-preview-title">Top live matches</p>
              <p className="subtle">The search preview blends tracked movie metadata with entity relationships.</p>
            </div>
            <Link className="search-preview-link" href={`/search?q=${encodeURIComponent(deferredQuery.trim())}`}>
              View full result set
            </Link>
          </div>

          <div className="search-preview-grid">
            <div className="search-preview-column">
              {previewItems.map((item) => (
                <Link className="suggestion-row suggestion-row-premium" href={`/movies/${item.slug}`} key={item.id}>
                  <div>
                    <strong>{item.title}</strong>
                    <span className="meta suggestion-supporting-copy">
                      {item.status} • {formatReleaseDate(item.release_date)}
                    </span>
                  </div>
                  <div className="suggestion-metrics">
                    <span>Hype {item.hype_score}</span>
                    <span>Buzz {item.buzz_score}</span>
                  </div>
                </Link>
              ))}
            </div>

            <div className="search-preview-column entity-preview-column">
              <EntitySection
                hrefPrefix="/studios"
                icon={<Building2 size={15} />}
                items={entityPreview.studios}
                title="Studios"
              />
              <EntitySection
                hrefPrefix="/franchises"
                icon={<Clapperboard size={15} />}
                items={entityPreview.franchises}
                title="Franchises"
              />
              <EntitySection
                hrefPrefix="/people"
                icon={<Users size={15} />}
                items={entityPreview.people}
                title="Talent"
              />
              <EntitySection
                hrefPrefix="/genres"
                icon={<Sparkles size={15} />}
                items={entityPreview.genres}
                title="Genres"
              />
            </div>
          </div>
        </div>
      ) : deferredQuery.trim().length > 1 && !searchPreviewQuery.isLoading ? (
        <div className="search-suggestions panel premium-search-suggestions">
          <p className="subtle">No quick matches yet. Run a full search to scan the broader catalog.</p>
        </div>
      ) : null}
    </div>
  )
}

function buildCapabilityActions({
  query,
  previewItems,
  entityPreview,
}: {
  query: string
  previewItems: MovieSummary[]
  entityPreview: ReturnType<typeof buildEntityPreview>
}) {
  const normalizedQuery = query.trim()
  const defaultMovie = previewItems[0]
  const topStudio = entityPreview.studios[0]
  const topTalent = entityPreview.people[0]
  const topFranchise = entityPreview.franchises[0]

  return [
    {
      label: 'Instant suggestions',
      hint: defaultMovie ? `Open ${defaultMovie.title}` : 'Try a guided query',
      href: defaultMovie ? `/movies/${defaultMovie.slug}` : normalizedQuery || 'oppenheimer',
      icon: Sparkles,
      mode: defaultMovie ? 'route' : 'query',
    },
    {
      label: 'Studio discovery',
      hint: topStudio || 'Browse by company',
      href: topStudio ? `/studios/${encodeURIComponent(topStudio)}` : normalizedQuery || 'warner bros',
      icon: Building2,
      mode: topStudio ? 'route' : 'query',
    },
    {
      label: 'Talent paths',
      hint: topTalent || 'Follow cast and crew',
      href: topTalent ? `/people/${encodeURIComponent(topTalent)}` : normalizedQuery || 'christopher nolan',
      icon: Users,
      mode: topTalent ? 'route' : 'query',
    },
    {
      label: 'Franchise context',
      hint: topFranchise || 'Jump into a series',
      href: topFranchise ? `/franchises/${encodeURIComponent(topFranchise)}` : normalizedQuery || 'dune',
      icon: Clapperboard,
      mode: topFranchise ? 'route' : 'query',
    },
  ] satisfies {
    label: string
    hint: string
    href: string
    icon: LucideIcon
    mode: 'route' | 'query'
  }[]
}

function EntitySection({
  title,
  hrefPrefix,
  items,
  icon,
}: {
  title: string
  hrefPrefix: string
  items: string[]
  icon: ReactNode
}) {
  if (!items.length) {
    return null
  }

  return (
    <div className="entity-preview-section">
      <div className="entity-preview-heading">
        {icon}
        <span>{title}</span>
      </div>
      <div className="entity-preview-tags">
        {items.map((item) => (
          <Link className="entity-preview-tag" href={`${hrefPrefix}/${encodeURIComponent(item)}`} key={item}>
            {item}
          </Link>
        ))}
      </div>
    </div>
  )
}

function buildEntityPreview(items: MovieSummary[]) {
  return {
    studios: topValues(items.flatMap((item) => item.studios), 4),
    franchises: topValues(items.flatMap((item) => (item.franchise ? [item.franchise] : [])), 4),
    people: topValues(
      items.flatMap((item) => [...item.directors, ...item.cast]),
      5,
    ),
    genres: topValues(items.flatMap((item) => item.genres), 5),
  }
}

function topValues(values: string[], limit: number) {
  const counts = new Map<string, number>()
  for (const value of values) {
    counts.set(value, (counts.get(value) || 0) + 1)
  }

  return [...counts.entries()]
    .sort((left, right) => {
      if (right[1] !== left[1]) {
        return right[1] - left[1]
      }
      return left[0].localeCompare(right[0])
    })
    .slice(0, limit)
    .map(([value]) => value)
}
