import { WatchlistButton } from './WatchlistButton'
import type { MovieAnalytics, MovieDetail } from '@/lib/api'
import { formatCompactNumber, formatCurrency, formatReleaseDate } from '@/lib/formatters'

export function MovieHero({
  movie,
  analytics,
}: {
  movie: MovieDetail
  analytics: MovieAnalytics
}) {
  const backdrop = movie.backdrop_url || movie.poster_url
  const openingLabel = analytics.forecast_is_public
    ? movie.status === 'released'
      ? 'Modeled Opening'
      : 'Projected Opening Weekend'
    : 'Opening Weekend'
  const openingValue = analytics.forecast_is_public && analytics.predicted_opening_weekend_usd > 0
    ? formatCurrency(analytics.predicted_opening_weekend_usd)
    : 'Unavailable'

  return (
    <section className="hero-panel movie-hero-panel">
      {backdrop ? (
        <div className="movie-hero-backdrop-shell">
          <img alt={movie.title} className="movie-backdrop" src={backdrop} />
        </div>
      ) : null}
      <div className="movie-hero-copy">
        <WatchlistButton movieId={movie.id} />
        <span className="eyebrow">{movie.status}</span>
        <div className="title-row movie-hero-title-row" style={{ marginTop: 16 }}>
          <div className="movie-hero-title-block">
            {movie.logo_url ? <img alt={`${movie.title} logo`} className="movie-logo" src={movie.logo_url} /> : null}
            <h1 style={{ margin: 0, fontSize: 'clamp(2.2rem, 5vw, 4rem)' }}>{movie.title}</h1>
            <p className="meta" style={{ marginTop: 12 }}>
              {formatReleaseDate(movie.release_date)} • {movie.genres.join(' • ')} {movie.runtime ? `• ${movie.runtime}` : ''}
            </p>
          </div>
          <div className="score-pill">{analytics.hype_score}</div>
        </div>
        <p className="hero-copy movie-hero-overview" style={{ marginTop: 18 }}>
          {movie.overview}
        </p>
        <div className="genre-list" style={{ marginTop: 18 }}>
          {movie.imdb_rating ? <span className="genre-tag">IMDb {movie.imdb_rating}</span> : null}
          {movie.rotten_tomatoes ? <span className="genre-tag">RT {movie.rotten_tomatoes}</span> : null}
          {movie.box_office ? <span className="genre-tag">Box Office {movie.box_office}</span> : null}
          {movie.franchise ? <span className="genre-tag">{movie.franchise}</span> : null}
        </div>
        <div className="metrics-grid" style={{ marginTop: 20 }}>
          <div className="metric-card">
            <div className="metric-label">Estimated Trailer Reach</div>
            <div className="metric-value">{formatCompactNumber(analytics.youtube_views)}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Estimated Social Mentions</div>
            <div className="metric-value">{formatCompactNumber(analytics.social_mentions)}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Estimated Search Demand</div>
            <div className="metric-value">{analytics.google_trends_score}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">{openingLabel}</div>
            <div className="metric-value">{openingValue}</div>
          </div>
        </div>
        {analytics.forecast_note || analytics.engagement_metrics_note || movie.warnings.length ? (
          <p className="meta" style={{ marginTop: 16 }}>
            {[analytics.forecast_note, analytics.engagement_metrics_note, movie.warnings[0]].filter(Boolean).join(' ')}
          </p>
        ) : null}
      </div>
    </section>
  )
}
