'use client'

import { useQuery } from '@tanstack/react-query'

import { movieApi, type MovieSummary } from '@/lib/api'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/QueryState'

import { MovieCard } from '../shared/MovieCard'

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

  return (
    <div className="section-grid">
      {data?.map((movie) => <MovieCard key={movie.id} movie={movie} />)}
    </div>
  )
}
