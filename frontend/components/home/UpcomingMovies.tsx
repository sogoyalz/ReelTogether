'use client'

import { useQuery } from '@tanstack/react-query'

import { movieApi } from '@/lib/api'
import { ErrorState, LoadingState } from '@/components/shared/QueryState'

import { MovieCard } from '../shared/MovieCard'

export function UpcomingMovies() {
  const { data, isLoading } = useQuery({
    queryKey: ['upcoming-movies'],
    queryFn: () => movieApi.getUpcoming(),
  })

  if (isLoading) {
    return <LoadingState title="Loading upcoming slate" description="Pulling the next release wave into the homepage." />
  }

  if (!data?.length) {
    return <ErrorState title="Upcoming slate unavailable" description="The upcoming feed did not return any titles." />
  }

  return (
    <div className="section-grid">
      {data?.map((movie) => <MovieCard key={movie.id} movie={movie} />)}
    </div>
  )
}
