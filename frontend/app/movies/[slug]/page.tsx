'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'

import { BoxOfficeHistoryChart } from '@/components/movies/BoxOfficeHistoryChart'
import { HypeGauge } from '@/components/movies/HypeGauge'
import { InterestChart } from '@/components/movies/InterestChart'
import { MovieHero } from '@/components/movies/MovieHero'
import { ScoreBreakdownCard } from '@/components/movies/ScoreBreakdownCard'
import { TrendChart } from '@/components/movies/TrendChart'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/QueryState'
import { movieApi } from '@/lib/api'
import { formatCompactNumber, formatCurrency } from '@/lib/formatters'

export default function MoviePage({ params }: { params: { slug: string } }) {
  const movieQuery = useQuery({
    queryKey: ['movie', params.slug],
    queryFn: () => movieApi.getMovieBySlug(params.slug),
  })

  const analyticsQuery = useQuery({
    queryKey: ['movie-analytics', movieQuery.data?.id],
    queryFn: () => movieApi.getAnalytics(movieQuery.data!.id),
    enabled: Boolean(movieQuery.data?.id),
  })
  const historyQuery = useQuery({
    queryKey: ['movie-history', movieQuery.data?.id],
    queryFn: () => movieApi.getAnalyticsHistory(movieQuery.data!.id),
    enabled: Boolean(movieQuery.data?.id),
  })

  if (movieQuery.isLoading || analyticsQuery.isLoading || historyQuery.isLoading) {
    return (
      <main className="page-shell">
        <LoadingState title="Loading movie analytics" description="Building the full movie detail surface and charts." />
      </main>
    )
  }

  if (movieQuery.isError || analyticsQuery.isError || historyQuery.isError) {
    return (
      <main className="page-shell">
        <ErrorState title="Movie detail unavailable" description="This movie page could not be loaded right now." />
      </main>
    )
  }

  if (!movieQuery.data || !analyticsQuery.data || !historyQuery.data) {
    return (
      <main className="page-shell">
        <EmptyState title="Movie not found" description="The requested movie is not in the current catalog." />
      </main>
    )
  }

  const movie = movieQuery.data
  const analytics = analyticsQuery.data
  const history = historyQuery.data

  return (
    <main className="page-shell">
      <Link className="eyebrow" href="/">
        Back to home
      </Link>
      <div className="hero-actions" style={{ marginTop: 16 }}>
        {movie.franchise ? <Link className="genre-tag" href={`/franchises/${encodeURIComponent(movie.franchise)}`}>{movie.franchise}</Link> : null}
        {movie.genres.map((genre) => <Link className="genre-tag" href={`/genres/${encodeURIComponent(genre)}`} key={genre}>{genre}</Link>)}
      </div>
      <div style={{ marginTop: 18 }}>
        <MovieHero analytics={analytics} movie={movie} />
      </div>

      <div className="detail-grid" style={{ marginTop: 28 }}>
        <div className="stack">
          <div className="panel">
            <div className="section-header" style={{ marginTop: 0 }}>
              <div>
                <h3>Editorial Snapshot</h3>
                <p>A compact read on ratings, release timing, franchise context, and where the title currently sits.</p>
              </div>
            </div>
            <div className="overview-grid">
              <div className="metric-card">
                <div className="metric-label">Release Status</div>
                <div className="metric-value overview-title">{movie.status}</div>
                <p className="meta">{movie.franchise || 'Standalone release'}</p>
              </div>
              <div className="metric-card">
                <div className="metric-label">Ratings Stack</div>
                <div className="metric-value overview-title">{movie.imdb_rating ? `${movie.imdb_rating}/10` : 'n/a'}</div>
                <p className="meta">{movie.rotten_tomatoes || 'No Rotten Tomatoes score yet'}</p>
              </div>
              <div className="metric-card">
                <div className="metric-label">Streaming</div>
                <div className="metric-value overview-title">{movie.streaming_on[0] || 'n/a'}</div>
                <p className="meta">{movie.streaming_on.slice(1).join(', ') || 'No streaming availability listed yet'}</p>
              </div>
            </div>
          </div>
          <InterestChart analytics={analytics} />
          <TrendChart history={history} />
          <BoxOfficeHistoryChart movie={movie} />
          <div className="panel">
            <div className="section-header" style={{ marginTop: 0 }}>
              <div>
                <h3>Cross-Platform Detail</h3>
                <p>Expanded detail for trailer performance, creative team, streaming, and projected demand.</p>
              </div>
            </div>
            <table className="table">
              <tbody>
                <tr>
                  <td>Franchise</td>
                  <td>{movie.franchise ? <Link href={`/franchises/${encodeURIComponent(movie.franchise)}`}>{movie.franchise}</Link> : 'Standalone'}</td>
                </tr>
                <tr>
                  <td>Studios</td>
                  <td>{movie.studios.map((studio) => <Link className="inline-chip" href={`/studios/${encodeURIComponent(studio)}`} key={studio}>{studio}</Link>)}</td>
                </tr>
                <tr>
                  <td>Directors</td>
                  <td>{movie.directors.map((person) => <Link className="inline-chip" href={`/people/${encodeURIComponent(person)}`} key={person}>{person}</Link>)}</td>
                </tr>
                <tr>
                  <td>Writers</td>
                  <td>{movie.writers.join(', ') || 'Not available'}</td>
                </tr>
                <tr>
                  <td>Lead Cast</td>
                  <td>{movie.cast.map((person) => <Link className="inline-chip" href={`/people/${encodeURIComponent(person)}`} key={person}>{person}</Link>)}</td>
                </tr>
                <tr>
                  <td>Streaming</td>
                  <td>{movie.streaming_on.join(', ') || 'Not available'}</td>
                </tr>
                <tr>
                  <td>IMDb Rating</td>
                  <td>{movie.imdb_rating ? `${movie.imdb_rating}/10` : 'Not available'}</td>
                </tr>
                <tr>
                  <td>Rotten Tomatoes</td>
                  <td>{movie.rotten_tomatoes || 'Not available'}</td>
                </tr>
                <tr>
                  <td>Runtime</td>
                  <td>{movie.runtime || 'Not available'}</td>
                </tr>
                <tr>
                  <td>Rated</td>
                  <td>{movie.rated || 'Not available'}</td>
                </tr>
                <tr>
                  <td>Awards</td>
                  <td>{movie.awards || 'Not available'}</td>
                </tr>
                <tr>
                  <td>Reported Box Office</td>
                  <td>{movie.box_office || 'Not available'}</td>
                </tr>
                <tr>
                  <td>YouTube Likes</td>
                  <td>{formatCompactNumber(analytics.youtube_likes)}</td>
                </tr>
                <tr>
                  <td>YouTube Comments</td>
                  <td>{formatCompactNumber(analytics.youtube_comments)}</td>
                </tr>
                <tr>
                  <td>X Mentions</td>
                  <td>{formatCompactNumber(analytics.x_mentions)}</td>
                </tr>
                <tr>
                  <td>Reddit Mentions</td>
                  <td>{formatCompactNumber(analytics.reddit_mentions)}</td>
                </tr>
                <tr>
                  <td>Predicted Domestic Total</td>
                  <td>{formatCurrency(analytics.predicted_domestic_total_usd)}</td>
                </tr>
                <tr>
                  <td>IMDb Votes</td>
                  <td>{movie.imdb_votes || 'Not available'}</td>
                </tr>
                <tr>
                  <td>Metascore</td>
                  <td>{movie.metascore || 'Not available'}</td>
                </tr>
                <tr>
                  <td>Trailer</td>
                  <td>
                    {analytics.trailer_url ? (
                      <a href={analytics.trailer_url} rel="noopener noreferrer" target="_blank">
                        Watch on YouTube
                      </a>
                    ) : 'Trailer not available'}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          {movie.trailer_embed_url ? (
            <div className="panel">
              <div className="section-header" style={{ marginTop: 0 }}>
                <div>
                  <h3>Trailer</h3>
                  <p>Embedded trailer view for quick context without leaving the page.</p>
                </div>
              </div>
              <div className="video-shell">
                <iframe
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                  src={movie.trailer_embed_url}
                  title={`${movie.title} trailer`}
                />
              </div>
            </div>
          ) : (
            <EmptyState
              title="No trailer embed yet"
              description="A trailer link has not been attached to this movie, so the page falls back to stats and editorial context."
            />
          )}
          {movie.backdrops.length ? (
            <div className="panel">
              <div className="section-header" style={{ marginTop: 0 }}>
                <div>
                  <h3>Image Gallery</h3>
                  <p>TMDB backdrop stills pulled into the detail page for richer visual context.</p>
                </div>
              </div>
              <div className="poster-strip">
                {movie.backdrops.map((backdrop) => (
                  <img alt={`${movie.title} backdrop`} className="gallery-image" key={backdrop} src={backdrop} />
                ))}
              </div>
            </div>
          ) : null}
        </div>
        <div className="stack">
          <HypeGauge analytics={analytics} />
          <ScoreBreakdownCard analytics={analytics} />
          <div className="panel">
            <div className="section-header" style={{ marginTop: 0 }}>
              <div>
                <h3>Quick Read</h3>
                <p>A faster scan for the movie’s critical and commercial context.</p>
              </div>
            </div>
            <div className="compare-stat-grid">
              <div>
                <div className="metric-label">Reported Box Office</div>
                <div>{movie.box_office || 'n/a'}</div>
              </div>
              <div>
                <div className="metric-label">Awards</div>
                <div>{movie.awards || 'n/a'}</div>
              </div>
              <div>
                <div className="metric-label">Metascore</div>
                <div>{movie.metascore || 'n/a'}</div>
              </div>
              <div>
                <div className="metric-label">IMDb Votes</div>
                <div>{movie.imdb_votes || 'n/a'}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
