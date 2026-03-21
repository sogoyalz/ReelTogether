'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'

import { movieApi } from '@/lib/api'
import { ErrorState, LoadingState } from '@/components/shared/QueryState'

import { MovieCard } from '../shared/MovieCard'

export function ReleasedMovies() {
  const { data, isLoading } = useQuery({
    queryKey: ['released-movies', 4],
    queryFn: () => movieApi.getReleased(4),
  })

  if (isLoading) {
    return <LoadingState title="Loading released titles" description="Pulling established releases into the homepage." />
  }

  if (!data?.length) {
    return <ErrorState title="Released titles unavailable" description="The released catalog feed returned no movies." />
  }

  return (
    <>
      <div className="section-grid">
        {data?.map((movie) => <MovieCard key={movie.id} movie={movie} />)}
      </div>
      <div className="section-footer">
        <Link className="cta-button" href="/movies">
          Browse full library
        </Link>
      </div>
    </>
  )
}
