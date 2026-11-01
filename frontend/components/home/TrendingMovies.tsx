'use client'

import { useQuery } from '@tanstack/react-query'

import { movieApi, type MovieSummary } from '@/lib/api'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/QueryState'

import { MovieCard } from '../shared/MovieCard'

export function TrendingMovies({ movies }: { movies?: MovieSummary[] }) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['trending-movies'],
    queryFn: () => movieApi.getTrending(),
    initialData: movies,
  })

  if (isLoading) {
    return <LoadingState title="Loading trending titles" description="Finding the strongest current attention signals." />
  }

  if (isError) return <ErrorState title="Could not load trending titles" description="Check your connection and try again." onRetry={() => void refetch()} />
  if (!data?.length) return <EmptyState title="No trending titles yet" description="The catalog has no matching films right now. Try browsing the library." />

  return (
    <div className="section-grid">
      {data?.map((movie) => <MovieCard key={movie.id} movie={movie} />)}
    </div>
  )
}
