'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'

import { movieApi, type MovieSummary } from '@/lib/api'
import { EmptyState, ErrorState } from '@/components/shared/QueryState'

import { MovieGridSkeleton } from '@/components/shared/MovieGridSkeleton'
import { MovieCard } from '../shared/MovieCard'

export function ReleasedMovies({ movies }: { movies?: MovieSummary[] }) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['released-movies', 4],
    queryFn: () => movieApi.getReleased(4),
    initialData: movies,
  })

  if (isLoading) {
    return <MovieGridSkeleton title="Loading released titles" count={4} />
  }

  if (isError) return <ErrorState title="Could not load released titles" description="Check your connection and try again." onRetry={() => void refetch()} />
  if (!data?.length) return <EmptyState title="No released titles yet" description="The catalog has no matching films right now. Try browsing the library." />

  return (
    <>
      <div className="section-grid released-grid">
        {data?.map((movie) => <MovieCard key={movie.id} movie={movie} wide />)}
      </div>
      <div className="section-footer">
        <Link className="cta-button" href="/movies">
          Browse full library
        </Link>
      </div>
    </>
  )
}
