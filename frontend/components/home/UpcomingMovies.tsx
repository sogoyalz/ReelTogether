'use client'

import { useQuery } from '@tanstack/react-query'

import { movieApi, type MovieSummary } from '@/lib/api'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/QueryState'

import Link from 'next/link'
import { ArrowUpRight } from 'lucide-react'
import { MovieArtwork } from '../shared/MovieArtwork'

export function UpcomingMovies({ movies }: { movies?: MovieSummary[] }) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['upcoming-movies', 'home', 6],
    queryFn: () => movieApi.getUpcoming(),
    initialData: movies,
  })

  if (isLoading) {
    return <LoadingState title="Loading upcoming slate" description="Pulling the next release wave into the homepage." />
  }

  if (isError) return <ErrorState title="Could not load upcoming titles" description="Check your connection and try again." onRetry={() => void refetch()} />
  if (!data?.length) return <EmptyState title="No upcoming titles yet" description="The catalog has no matching films right now. Try browsing the library." />

  return <div className="release-list">{data.map(movie => {
    const date = new Date(movie.release_date)
    return <Link className="release-row" href={`/movies/${movie.slug}`} key={movie.id}><div className="release-date"><strong>{movie.status === 'announced' ? '—' : date.getUTCDate().toString().padStart(2,'0')}</strong><span>{movie.status === 'announced' ? 'Announced' : date.toLocaleDateString('en-US',{month:'short',timeZone:'UTC'})}</span></div><div className="release-poster"><MovieArtwork src={movie.poster_url} title={movie.title}/></div><div className="release-copy"><h3>{movie.title}</h3><span className="meta">{movie.release_date.slice(0,4)} · {movie.genres.slice(0,2).join(' / ') || 'On the horizon'}</span></div><ArrowUpRight size={17}/></Link>
  })}</div>
}
