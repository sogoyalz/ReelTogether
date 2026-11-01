'use client'

import { useParams } from 'next/navigation'
import { useState } from 'react'
import Link from 'next/link'
import dynamic from 'next/dynamic'
import { useQuery } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { MovieHero } from '@/components/movies/MovieHero'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/QueryState'
import { movieApi } from '@/lib/api'

const MovieInsights = dynamic(() => import('@/components/movies/MovieInsights').then(module => module.MovieInsights), { loading: () => <LoadingState title="Opening film insights" description="Loading the stored analysis and film context."/> })

export default function MoviePage() {
  const params = useParams<{ slug: string }>()
  const [insightsOpen,setInsightsOpen] = useState(false)
  const movieQuery = useQuery({ queryKey:['movie',params.slug], queryFn:()=>movieApi.getMovieBySlug(params.slug), retry: (count, error) => !(isAxiosError(error) && error.response?.status === 404) && count < 3 })
  if (movieQuery.isLoading) {
    return (
      <main className="page-shell">
        <LoadingState title="Loading your movie" description="Finding the story, cast, and details." />
      </main>
    )
  }

  if (movieQuery.isError) {
    return (
      <main className="page-shell">
        {isAxiosError(movieQuery.error) && movieQuery.error.response?.status === 404
          ? <EmptyState title="Movie not found" description="The requested movie is not in the current catalog." />
          : <ErrorState title="Movie detail unavailable" description="This movie page could not be loaded right now." onRetry={()=>void movieQuery.refetch()} />}
      </main>
    )
  }

  if (!movieQuery.data) {
    return (
      <main className="page-shell">
        <EmptyState title="Movie not found" description="The requested movie is not in the current catalog." />
      </main>
    )
  }

  const movie = movieQuery.data
  return (
    <main className="page-shell">
      <Link className="eyebrow" href="/">
        Back to home
      </Link>
      <MovieHero movie={movie} />
      <section className="cinema-film-facts" aria-label="Film details">
        {movie.directors.length > 0 && <div><span>Directed by</span><p>{movie.directors.map((person, index) => <span key={person}>{index > 0 && ', '}<Link href={`/people/${encodeURIComponent(person)}`}>{person}</Link></span>)}</p></div>}
        {movie.cast.length > 0 && <div><span>Starring</span><p>{movie.cast.slice(0, 5).join(' · ')}</p></div>}
        {movie.streaming_on.length > 0 && <div><span>Streaming platforms</span><p>{movie.streaming_on.join(' · ')}</p><small>{movie.field_sources.streaming_on === 'generated' ? 'Illustrative availability. ' : 'Availability data: JustWatch via TMDB. '}Availability varies by region. <a href="https://www.justwatch.com/" rel="noreferrer">Check availability</a></small></div>}
      </section>
      {movie.trailer_embed_url && <section className="cinema-trailer"><div className="section-header"><h2>A first look</h2></div><div className="video-shell"><iframe loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen src={movie.trailer_embed_url} title={`${movie.title} trailer`} /></div></section>}
      {movie.warnings.length > 0 && <p className="meta cinema-source-note">{movie.warnings[0]}</p>}
      <details onToggle={event => setInsightsOpen(event.currentTarget.open)} className="cinema-details">
        <summary>Go deeper <span>Audience insights, film context &amp; detailed analytics</span></summary>
        {insightsOpen && <MovieInsights movie={movie} />}
      </details>
    </main>
  )
}
