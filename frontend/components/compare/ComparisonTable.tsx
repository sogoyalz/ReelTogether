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
            <th>AI Sentiment</th>
            <th>Confidence</th>
            <th>Buzz</th>
            <th>Hype</th>
            <th>Views</th>
            <th>Social</th>
            <th>Search</th>
            <th>Live Sentiment</th>
            <th>Opening</th>
            <th>Domestic</th>
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
              <td>{item.prediction_confidence !== null ? `${Math.round(item.prediction_confidence * 100)}%` : 'n/a'}</td>
              <td>{item.buzz_score}</td>
              <td>{item.hype_score}</td>
              <td>{formatCompactNumber(item.youtube_views)}</td>
              <td>{formatCompactNumber(item.social_mentions)}</td>
              <td>{item.google_trends_score}</td>
              <td>{Math.round(item.sentiment_score * 100)}%</td>
              <td>{formatCurrency(item.predicted_opening_weekend_usd)}</td>
              <td>{formatCurrency(item.predicted_domestic_total_usd)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
