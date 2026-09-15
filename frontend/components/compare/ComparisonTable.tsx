import type { ComparisonItem } from '@/lib/api'
import { formatCompactNumber, formatCurrency, formatReleaseDate } from '@/lib/formatters'

export function ComparisonTable({ items }: { items: ComparisonItem[] }) {
  return (
    <div className="panel">
      <div className="section-header" style={{ marginTop: 0 }}>
        <div>
          <h3>Comparison Table</h3>
          <p>Quick numeric view across attention, ratings, franchise context, release timing, and revenue potential.</p>
        </div>
      </div>
      <div className="table-shell" tabIndex={0} role="region" aria-label="Movie comparison table">
      <table className="table">
        <thead>
          <tr>
            <th>Movie</th>
            <th>Status</th>
            <th>Release</th>
            <th>Franchise</th>
            <th>Popularity</th>
            <th>IMDb</th>
            <th>RT</th>
            <th>Runtime</th>
            <th>Streaming</th>
            <th>Audience sentiment</th>
            <th>Forecast validation</th>
            <th>Buzz</th>
            <th>Hype</th>
            <th>Est. Views</th>
            <th>Est. Social</th>
            <th>Search</th>
            <th>Est. Sentiment</th>
            <th>Opening Model</th>
            <th>Domestic Model</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.movie_id}>
              <td>{item.title}</td>
              <td>{item.status}</td>
              <td>{formatReleaseDate(item.release_date)}</td>
              <td>{item.franchise || 'Standalone'}</td>
              <td>{item.tmdb_popularity.toFixed(1)}</td>
              <td>{item.imdb_rating || 'n/a'}</td>
              <td>{item.rotten_tomatoes || 'n/a'}</td>
              <td>{item.runtime || 'n/a'}</td>
              <td>{item.streaming_on.length ? item.streaming_on.join(', ') : 'n/a'}</td>
              <td>{item.audience_sentiment !== null ? `${Math.round(item.audience_sentiment * 100)}%` : 'n/a'}</td>
              <td>Unvalidated</td>
              <td>{item.buzz_score}</td>
              <td>{item.hype_score}</td>
              <td>{formatCompactNumber(item.youtube_views)}</td>
              <td>{formatCompactNumber(item.social_mentions)}</td>
              <td>{item.google_trends_score}</td>
              <td>{Math.round(item.sentiment_score * 100)}%</td>
              <td>{item.forecast_is_public && item.predicted_opening_weekend_usd > 0 ? formatCurrency(item.predicted_opening_weekend_usd) : 'n/a'}</td>
              <td>{item.forecast_is_public && item.predicted_domestic_total_usd > 0 ? formatCurrency(item.predicted_domestic_total_usd) : 'n/a'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </div>
  )
}
