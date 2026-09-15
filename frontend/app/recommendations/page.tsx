'use client'

import { FormEvent, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowUp, MessageCircle, RotateCcw, SlidersHorizontal, Laugh, Rocket, Heart, ShieldCheck } from 'lucide-react'
import { api, movieApi } from '@/lib/api'
import { accountError, csrfHeaders, useAccount, type AuthState } from '@/lib/account'
import { MovieArtwork } from '@/components/shared/MovieArtwork'
import { WatchlistButton } from '@/components/movies/WatchlistButton'

type Filters = { genres: string[]; excluded_genres: string[]; languages: string[]; max_runtime: number | null }
type Feedback = { movie_id: number; title: string; release_date: string; preference: 'like' | 'dislike' }
type Pick = { movie: { id: number; slug: string; poster_url?: string | null; title: string; release_date: string; genres: string[]; runtime: number | null; languages: string[] }; reasons: string[] }
type Answer = { reply: string; filters: Filters; favorite_ids?: number[]; items: Pick[]; needs_clarification: boolean; mode: string; action?: string }
const emptyFilters = (): Filters => ({ genres: [], excluded_genres: [], languages: [], max_runtime: null })
const genres = ['Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Documentary', 'Drama', 'Family', 'Fantasy', 'History', 'Horror', 'Music', 'Mystery', 'Romance', 'Science Fiction', 'Thriller', 'War', 'Western']
const languages = ['English', 'Hindi', 'Tamil', 'Telugu', 'Malayalam', 'Kannada', 'Korean', 'Japanese', 'French', 'Spanish']

export default function RecommendationsPage() {
  const account = useAccount()
  if (account.isPending) return <main className="page-shell"><p role="status">Opening Movie Match…</p></main>
  if (account.isError) return <main className="page-shell"><p role="alert">Could not check your session.</p><button className="cta-button" onClick={() => account.refetch()}>Retry</button></main>
  return <MovieAssistant key={account.data?.user.id ?? 'guest'} auth={account.data ?? null} />
}

function MovieAssistant({ auth }: { auth: AuthState | null }) {
  const client = useQueryClient()
  const [filters, setFilters] = useState<Filters>(emptyFilters)
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; text: string }[]>([])
  const [picks, setPicks] = useState<Pick[]>([])
  const [guestFeedback, setGuestFeedback] = useState<Feedback[]>([])
  const [referenceIds, setReferenceIds] = useState<number[]>([])
  const [seen, setSeen] = useState<number[]>([])
  const [busy, setBusy] = useState(false)
  const [useAI, setUseAI] = useState(false)
  const [preferencesOpen, setPreferencesOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [feedbackNotice, setFeedbackNotice] = useState('')
  const [search, setSearch] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const conversationEnd = useRef<HTMLDivElement>(null)
  const requestLock = useRef(false)
  useEffect(() => { const timer = setTimeout(() => setSearchTerm(search.trim()), 250); return () => clearTimeout(timer) }, [search])
  useEffect(() => {
    if (!messages.length && !busy) return
    const log = conversationEnd.current?.parentElement
    log?.scrollTo({ top: log.scrollHeight, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
  }, [messages, busy])
  const spotlight = useQuery({ queryKey: ['match-spotlight'], queryFn: async () => (await movieApi.browseCatalog({ status: 'released', sort: 'popularity', page_size: 5 })).items, staleTime: 300000 })
  const profile = useQuery({
    queryKey: ['movie-feedback', auth?.user.id], enabled: Boolean(auth),
    queryFn: async () => (await api.get<{ items: Feedback[] }>('/api/assistant/feedback')).data,
  })
  const coverage = useQuery({
    queryKey: ['recommendation-coverage'],
    queryFn: async () => (await api.get<{ released_movies: number; with_runtime: number; with_language: number; ai_available: boolean }>('/api/assistant/coverage')).data,
  })
  const suggestions = useQuery({
    queryKey: ['taste-search', searchTerm], enabled: searchTerm.length >= 2,
    queryFn: () => movieApi.searchSuggestions(searchTerm),
  })
  const feedback = auth ? profile.data?.items ?? [] : guestFeedback
  const favourites = feedback.filter(item => item.preference === 'like')
  const profileUnavailable = Boolean(auth && (profile.isPending || profile.isError))

  async function rate(item: Feedback, remove = false) {
    if (requestLock.current || saving) return
    setSaving(true); setError('')
    try {
      if (auth) {
        if (remove) await api.delete(`/api/assistant/feedback/${item.movie_id}`, { headers: csrfHeaders(auth) })
        else await api.put(`/api/assistant/feedback/${item.movie_id}`, { preference: item.preference }, { headers: csrfHeaders(auth) })
        await client.invalidateQueries({ queryKey: ['movie-feedback', auth.user.id] })
      } else {
        setGuestFeedback(current => [...current.filter(row => row.movie_id !== item.movie_id), ...(remove ? [] : [item])].slice(-100))
      }
      setReferenceIds(current => current.filter(id => id !== item.movie_id))
      setPicks(current => current.filter(pick => pick.movie.id !== item.movie_id))
      setSearch(''); setSearchTerm('')
      setFeedbackNotice(remove ? `Preference removed for ${item.title}.` : item.preference === 'like' ? `${item.title} added to your favourites.` : `${item.title} dismissed. You can undo this in your preferences.`)
    } catch (err) { setError(accountError(err)) }
    finally { setSaving(false) }
  }

  async function send(text: string) {
    if (!text.trim() || requestLock.current || saving || profileUnavailable) return
    requestLock.current = true
    setBusy(true); setError('')
    const isMore = /^(?:show\s+(?:me\s+)?)?more(?: please)?[.!?]*$/i.test(text.trim())
    try {
      const response = await api.post<Answer>('/api/assistant/chat', {
        message: text.trim(), filters, use_ai: useAI, seen_ids: seen,
        favorite_ids: Array.from(new Set([...referenceIds, ...(!auth ? favourites.map(item => item.movie_id) : [])])).slice(-20),
        excluded_ids: Array.from(new Set([...(isMore ? seen : []), ...feedback.filter(item => item.preference === 'dislike').map(item => item.movie_id)])).slice(-100),
      }, { headers: auth ? csrfHeaders(auth) : {}, timeout: 20000 })
      const answer = response.data
      setMessages(current => [...current, { role: 'user' as const, text: text.trim() }, { role: 'assistant' as const, text: answer.reply }].slice(-20))
      if (!answer.needs_clarification) {
        setFilters(answer.filters); setPicks(answer.items)
        setReferenceIds(answer.favorite_ids ?? [])
        setSeen(current => Array.from(new Set([...((isMore || answer.action === 'more') ? current : []), ...answer.items.map(item => item.movie.id)])).slice(-80))
      }
      setMessage('')
    } catch (err) { setError(accountError(err)) }
    finally { requestLock.current = false; setBusy(false) }
  }

  function reset() {
    if (busy) return
    setFilters(emptyFilters()); setMessages([]); setPicks([]); setSeen([]); setReferenceIds([]); setMessage(''); setError('')
  }
  function submit(event: FormEvent) { event.preventDefault(); void send(message) }

  return <main className="page-shell match-page">
    <p className="meta"><Link href="/movie-night">Watching with friends? Plan a Movie Night →</Link></p>
    <header className="match-heading">
      <div className="match-hero-copy"><p className="match-eyebrow">MOVIE MATCH · MADE FOR YOUR TASTE</p><h1>Less scrolling.<br /><em>More cinema.</em></h1><p className="subtle">A favourite film. A genre. A little inspiration.<br />Start with what you love. Find what to watch next.</p><a href="#movie-message" className="match-hero-link" onClick={event => { event.preventDefault(); document.getElementById('movie-message')?.focus() }}>Find your next film <ArrowUp size={16} aria-hidden="true" /></a></div>
      <div className="match-poster-gallery" aria-label="Explore movies from the catalog">
        {spotlight.data?.slice(0, 5).map(movie => <Link key={movie.id} href={`/movies/${movie.slug}`} className="match-hero-poster" aria-label={`Explore ${movie.title}`}><MovieArtwork src={movie.poster_url} title={movie.title} /><span>{movie.title}</span></Link>)}
        {!spotlight.data?.length && <div className="match-poster-placeholder"><MessageCircle size={48} /><span>There’s a film for every mood.</span></div>}
      </div>
    </header>
    <button className="match-mobile-preferences" aria-expanded={preferencesOpen} aria-controls="match-preferences" onClick={() => setPreferencesOpen(!preferencesOpen)}><SlidersHorizontal size={16} /> Your taste & filters <span>{preferencesOpen ? 'Close' : 'Edit'}</span></button>
    <div className={preferencesOpen ? 'match-layout preferences-open' : 'match-layout'}>

      <section className="match-main" aria-label="Movie recommendation chat">
        <div className={`panel match-chat ${messages.length || busy ? 'match-chat-active' : 'match-chat-empty'}`}>
          <div className="match-chat-heading"><h2>What are you in the mood for?</h2><button className="match-reset" onClick={reset} disabled={busy} aria-label="Start a new chat"><RotateCcw size={15} /> Start over</button></div>
          <p className="meta">{useAI ? 'Describe what you feel like watching. Review the interpreted filters before refining your shortlist.' : 'Try a genre or the title of a film you love. We’ll take it from there.'}</p>

          <div className="match-conversation" role="log" aria-label="Conversation" aria-live="polite">
            {messages.map((entry, index) => <div key={index} className={`match-message match-message-${entry.role}`}><strong>{entry.role === 'user' ? 'You' : 'Movie Match'}</strong><p>{entry.text}</p></div>)}
            {busy && <p className="match-thinking" role="status"><span className="thinking-dots" aria-hidden="true"><i /><i /><i /></span>Finding movies in the catalog…</p>}
            <div ref={conversationEnd} />
          </div>
          <div className="match-prompts">{[{ label: 'Make me laugh', query: 'Recommend a comedy', icon: Laugh, tone: 'amber' }, { label: 'Explore other worlds', query: 'Science fiction', icon: Rocket, tone: 'violet' }, { label: 'A little romance', query: 'Romance', icon: Heart, tone: 'rose' }, { label: 'Skip the scares', query: 'No horror', icon: ShieldCheck, tone: 'teal' }].map(({ label, query, icon: Icon, tone }) => <button className={`mood-chip mood-${tone}`} key={label} aria-label={query} disabled={busy || saving || profileUnavailable} onClick={() => send(query)}><Icon size={15} aria-hidden="true" />{label}</button>)}</div>
          <form className="match-composer" onSubmit={submit}><label className="sr-only" htmlFor="movie-message">Message Movie Match</label><input id="movie-message" autoComplete="off" value={message} onChange={event => setMessage(event.target.value)} maxLength={500} placeholder="e.g. Science fiction, without horror" disabled={busy} /><button className="cta-button" aria-label="Send message" disabled={busy || saving || !message.trim() || profileUnavailable}><ArrowUp size={20} /></button></form>
          <div className="match-ai-setting">
            <label><input type="checkbox" checked={useAI} disabled={busy || !auth || !coverage.data?.ai_available} onChange={event => setUseAI(event.target.checked)} /> Interpret my request</label>
            <p className="meta">{!coverage.data?.ai_available ? 'Request interpretation is not configured on this server. Catalog mode is available.' : !auth ? 'Sign in to use request interpretation.' : useAI ? 'Your message and current filters will be sent to an external interpretation service. Movie results come from this catalog.' : 'Optional. Enable for more natural movie requests.'}</p>
          </div>
          {error && <p role="alert">{error} Please try again.</p>}
        </div>
        {feedbackNotice && <p className="match-feedback-notice" role="status">{feedbackNotice}</p>}
        {picks.length > 0 && <section className="match-results" aria-label="Recommended movies"><div className="match-result-heading"><div><h2>Your shortlist</h2><p className="meta match-result-count">{picks.length} recommendations · Based on your current preferences</p></div><button disabled={busy || saving} onClick={() => send('show more')}>Show more</button></div><div className="match-picks">{picks.map(({ movie, reasons }) => <article className="panel match-pick" key={movie.id}>
          <Link className="match-pick-art" href={`/movies/${movie.slug}`} aria-label={`View ${movie.title}`}><MovieArtwork src={movie.poster_url} title={movie.title} /></Link><p className="match-eyebrow">{movie.genres.slice(0, 2).join(' · ')}</p><h3><Link href={`/movies/${movie.slug}`}>{movie.title}</Link></h3>
          <p className="meta">{movie.release_date.slice(0, 4)}{movie.runtime ? ` · ${movie.runtime} min` : ''}{movie.languages.length ? ` · ${movie.languages.join(', ')}` : ''}</p>
          <div className="match-reasons"><strong>Why this pick</strong>{reasons.map(reason => <p key={reason}>{reason}</p>)}</div>
          <div className="match-feedback"><button disabled={busy || saving} aria-label={`Like ${movie.title}`} onClick={() => rate({ movie_id: movie.id, title: movie.title, release_date: movie.release_date, preference: 'like' })}>I like this</button><button disabled={busy || saving} aria-label={`Dismiss ${movie.title}`} onClick={() => rate({ movie_id: movie.id, title: movie.title, release_date: movie.release_date, preference: 'dislike' })}>Not for me</button><Link href={`/movies/${movie.slug}`}>Details →</Link></div>
          {auth && <WatchlistButton movieId={movie.id} />}
        </article>)}</div></section>}
      </section>
      <aside id="match-preferences" className="panel match-preferences" aria-label="Recommendation preferences">
        <p className="match-eyebrow">MAKE IT PERSONAL</p><h2>Your preferences</h2>
        <p className="meta">Add films you enjoy to personalize your results.</p>
        <label className="match-label" htmlFor="favourite-search">Favourite movies ({favourites.length})</label>
        <input id="favourite-search" placeholder="Search a movie you love…" value={search} maxLength={100} onChange={event => setSearch(event.target.value)} disabled={busy || saving || profileUnavailable} />
        {searchTerm.length >= 2 && <div className="match-search-results">
          {suggestions.isPending && <p role="status">Searching the catalog…</p>}
          {suggestions.isError && <p role="alert">Movie search failed. Try again.</p>}
          {suggestions.data?.filter(item => !favourites.some(f => f.movie_id === item.id)).slice(0, 5).map(item => <button key={item.id} disabled={busy || saving || favourites.length >= 20} onClick={() => rate({ movie_id: item.id, title: item.title, release_date: item.release_date, preference: 'like' })}>Add {item.title} ({item.release_date.slice(0, 4)})</button>)}
          {suggestions.data?.length === 0 && <p className="meta">No title found. Try another spelling.</p>}
        </div>}
        <div className="match-favourites">{favourites.map(item => <button key={item.movie_id} disabled={busy || saving} aria-label={`Remove favourite ${item.title}`} onClick={() => rate(item, true)}>{item.title} <span aria-hidden="true">×</span></button>)}</div>
        {auth ? <p className="meta">Taste saved to your account. Watched movies are excluded.</p> : <p className="meta">Guest taste lasts while this page is open. <Link href="/watchlist">Sign in to keep it.</Link></p>}
        {profile.isError && <p role="alert">Could not load saved taste. <button onClick={() => profile.refetch()}>Retry</button></p>}
        <h3 className="match-filter-heading"><SlidersHorizontal size={16} aria-hidden="true" /> Your filters</h3>

        <fieldset disabled={busy} className="match-filter-fields">
          <label className="match-label" htmlFor="match-genre">Genre</label>
          <select id="match-genre" value={filters.genres.length === 1 ? filters.genres[0] : ''} onChange={event => setFilters({ ...filters, genres: event.target.value ? [event.target.value] : [], excluded_genres: filters.excluded_genres.filter(g => g !== event.target.value) })}><option value="">{filters.genres.length > 1 ? filters.genres.join(' or ') : 'Any genre'}</option>{genres.map(g => <option key={g}>{g}</option>)}</select>
          <label className="match-label" htmlFor="match-language">Language</label>
          <select id="match-language" value={filters.languages.length === 1 ? filters.languages[0] : ''} onChange={event => setFilters({ ...filters, languages: event.target.value ? [event.target.value] : [] })}><option value="">{filters.languages.length > 1 ? filters.languages.join(' or ') : 'Any language'}</option>{languages.map(l => <option key={l}>{l}</option>)}</select>
          <label className="match-label" htmlFor="match-runtime">Maximum runtime (minutes)</label>
          <input id="match-runtime" type="number" min={1} max={600} value={filters.max_runtime ?? ''} placeholder="Any runtime" onChange={event => setFilters({ ...filters, max_runtime: event.target.value ? Math.min(600, Math.max(1, Number(event.target.value))) : null })} />
          {filters.excluded_genres.length > 0 && <p className="meta">Excluding: {filters.excluded_genres.join(', ')} <button onClick={() => setFilters({ ...filters, excluded_genres: [] })}>Clear exclusions</button></p>}
        </fieldset>
        <details className="match-data-details"><summary>Catalog coverage & limitations</summary>{coverage.data && <p className="meta match-coverage">{coverage.data.released_movies} released movies. Runtime known for {coverage.data.with_runtime}; language known for {coverage.data.with_language}.{(!coverage.data.with_runtime || !coverage.data.with_language) && ' Missing details need a catalog refresh. Try genres and favourites in the meantime.'}</p>}<p className="meta">Unknown runtime or language cannot match an active filter. Streaming availability is not verified.</p></details>
        <button className="cta-button" disabled={busy || saving || profileUnavailable} onClick={() => send('recommend')}>Find my movies</button>
        {feedback.some(item => item.preference === 'dislike') && <details className="match-dismissed"><summary>Dismissed movies</summary>{feedback.filter(item => item.preference === 'dislike').map(item => <button key={item.movie_id} disabled={busy || saving} onClick={() => rate(item, true)}>Undo dismissal: {item.title}</button>)}</details>}
      </aside>
    </div>
  </main>
}
