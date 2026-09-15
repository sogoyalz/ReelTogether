'use client'

import Link from 'next/link'

import type { ComparisonItem } from '@/lib/api'
import { formatCompactNumber, formatCurrency, formatReleaseDate } from '@/lib/formatters'

const categoryMeta = [
  {
    key: 'buzz_score',
    label: 'Buzz',
    description: 'Current cross-platform attention lead.',
    format: (item: ComparisonItem) => item.buzz_score.toFixed(2),
  },
  {
    key: 'hype_score',
    label: 'Hype',
    description: 'Best overall hype score.',
    format: (item: ComparisonItem) => item.hype_score.toFixed(2),
  },
  {
    key: 'youtube_views',
    label: 'Estimated Reach',
    description: 'Largest modeled trailer audience so far.',
    format: (item: ComparisonItem) => formatCompactNumber(item.youtube_views),
  },
  {
    key: 'social_mentions',
    label: 'Estimated Chatter',
    description: 'Most visible modeled conversation volume.',
    format: (item: ComparisonItem) => formatCompactNumber(item.social_mentions),
  },
  {
    key: 'predicted_opening_weekend_usd',
    label: 'Opening Model',
    description: 'Strongest public theatrical forecast currently allowed.',
    format: (item: ComparisonItem) => (
      item.forecast_is_public && item.predicted_opening_weekend_usd > 0
        ? formatCurrency(item.predicted_opening_weekend_usd)
        : item.box_office || 'n/a'
    ),
  },
  {
    key: 'tmdb_popularity',
    label: 'Popularity',
    description: 'Highest current TMDB popularity signal.',
    format: (item: ComparisonItem) => item.tmdb_popularity.toFixed(1),
  },
]

export function ComparisonSpotlight({ items }: { items: ComparisonItem[] }) {
  const categoryWinners = categoryMeta.map((category) => {
    const winner = [...items].sort(
      (left, right) =>
        Number(right[category.key as keyof ComparisonItem]) - Number(left[category.key as keyof ComparisonItem]),
    )[0]

    return {
      ...category,
      winner,
    }
  })

  return (
    <div className="stack">
      <div className="panel">
        <div className="section-header" style={{ marginTop: 0 }}>
          <div>
            <h3>Winner Board</h3>
            <p>Quick category leaders before you dive into the full numbers.</p>
          </div>
        </div>
        <div className="section-grid">
          {categoryWinners.map((category) => (
            <div className="metric-card" key={category.key}>
              <div className="metric-label">{category.label}</div>
              <div className="metric-value" style={{ fontSize: '1.35rem' }}>
                {category.winner.title}
              </div>
              <p className="meta" style={{ marginTop: 10 }}>
                {category.description}
              </p>
              <div style={{ marginTop: 14, fontWeight: 700 }}>
                {category.format(category.winner)}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="compare-grid">
        {items.map((item) => (
          <div className="compare-card compare-spotlight-card" key={item.movie_id}>
            <div className="compare-card-body">
              <div className="title-row">
                <div>
                  <h3>{item.title}</h3>
                  <p className="meta">{formatReleaseDate(item.release_date)}</p>
                </div>
                <div className="score-pill">{item.hype_score}</div>
              </div>
              <div className="genre-list">
                <span className="genre-tag">Buzz {item.buzz_score}</span>
                <span className="genre-tag">Search {item.google_trends_score}</span>
                <span className="genre-tag">Popularity {item.tmdb_popularity.toFixed(1)}</span>
                {item.imdb_rating ? <span className="genre-tag">IMDb {item.imdb_rating}</span> : null}
                {item.rotten_tomatoes ? <span className="genre-tag">RT {item.rotten_tomatoes}</span> : null}
                {item.audience_sentiment !== null ? <span className="genre-tag">Sentiment {Math.round(item.audience_sentiment * 100)}%</span> : null}
              </div>
              <div className="compare-stat-grid">
                <div>
                  <div className="metric-label">Estimated Reach</div>
                  <div>{formatCompactNumber(item.youtube_views)}</div>
                </div>
                <div>
                  <div className="metric-label">Estimated Social</div>
                  <div>{formatCompactNumber(item.social_mentions)}</div>
                </div>
                <div>
                  <div className="metric-label">Sentiment</div>
                  <div>{Math.round(item.sentiment_score * 100)}%</div>
                </div>
                <div>
                  <div className="metric-label">{item.forecast_is_public ? 'Opening Model' : 'Reported Box Office'}</div>
                  <div>{item.forecast_is_public && item.predicted_opening_weekend_usd > 0 ? formatCurrency(item.predicted_opening_weekend_usd) : item.box_office || 'n/a'}</div>
                </div>
                <div>
                  <div className="metric-label">Runtime</div>
                  <div>{item.runtime || 'n/a'}</div>
                </div>
                <div>
                  <div className="metric-label">Franchise</div>
                  <div>{item.franchise || 'Standalone'}</div>
                </div>
                <div>
                  <div className="metric-label">Confidence</div>
                  <div>{item.prediction_confidence !== null ? `${Math.round(item.prediction_confidence * 100)}%` : 'n/a'}</div>
                </div>
                <div>
                  <div className="metric-label">{item.forecast_is_public ? 'Domestic Model' : 'Forecast Status'}</div>
                  <div>{item.forecast_is_public && item.predicted_domestic_total_usd > 0 ? formatCurrency(item.predicted_domestic_total_usd) : item.forecast_status}</div>
                </div>
              </div>
              {item.warnings.length ? (
                <p className="meta" style={{ marginTop: 14 }}>
                  {item.warnings[0]}
                </p>
              ) : null}
              {item.streaming_on.length ? (
                <div className="meta-line" style={{ marginTop: 14 }}>
                  <span className="meta-kicker">Streaming</span>
                  <span>{item.streaming_on.join(', ')}</span>
                </div>
              ) : null}
              {item.key_themes.length ? (
                <div className="meta-line" style={{ marginTop: 10, alignItems: 'flex-start' }}>
                  <span className="meta-kicker">Research</span>
                  <span>{item.key_themes.join(', ')}</span>
                </div>
              ) : null}
              <div style={{ marginTop: 18 }}>
                <Link className="cta-button secondary-button" href={`/movies/${item.slug}`}>
                  Open detail page
                </Link>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
