'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'

import { movieApi } from '@/lib/api'
import { formatCompactNumber, formatReleaseDate } from '@/lib/formatters'
import { ErrorState, LoadingState } from '@/components/shared/QueryState'

export function BuzzRanking() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: movieApi.getDashboard,
  })

  if (isLoading) {
    return <LoadingState title="Building the buzz board" description="Ranking the strongest multi-signal movie momentum right now." />
  }

  if (!data) {
    return <ErrorState title="Buzz board unavailable" description="The dashboard ranking could not be loaded." />
  }

  return (
    <div className="panel">
      <div className="section-header" style={{ marginTop: 0 }}>
        <div>
          <h3>Buzz Score Leaders</h3>
          <p>Multi-signal ranking using trailers, search momentum, and social chatter.</p>
        </div>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Movie</th>
            <th>Release</th>
            <th>Buzz</th>
            <th>Hype</th>
          </tr>
        </thead>
        <tbody>
          {data.trending.map((movie) => (
            <tr key={movie.id}>
              <td>
                <Link href={`/movies/${movie.slug}`}>{movie.title}</Link>
              </td>
              <td>{formatReleaseDate(movie.release_date)}</td>
              <td>{formatCompactNumber(movie.buzz_score)}</td>
              <td>{movie.hype_score}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
