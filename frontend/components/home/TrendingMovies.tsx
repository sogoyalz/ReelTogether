'use client'

import { useQuery } from '@tanstack/react-query'

import { movieApi, type MovieSummary } from '@/lib/api'
import { ErrorState, LoadingState } from '@/components/shared/QueryState'

import { MovieCard } from '../shared/MovieCard'

export function TrendingMovies({ movies }: { movies?: MovieSummary[] }) {
  const { data, isLoading } = useQuery({
    queryKey: ['trending-movies'],
    queryFn: () => movieApi.getTrending(),
    initialData: movies,
  })

  if (isLoading) {
    return <LoadingState title="Loading trending titles" description="Finding the strongest current attention signals." />
  }

  if (!data?.length) {
    return <ErrorState title="Trending titles unavailable" description="The trending feed returned no movies." />
  }

  return (
    <div className="section-grid">
      {data?.map((movie) => <MovieCard key={movie.id} movie={movie} />)}
    </div>
  )
}
