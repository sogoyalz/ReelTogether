import type { MovieAnalytics } from '@/lib/api'

export function HypeGauge({ analytics }: { analytics: MovieAnalytics }) {
  const positive = analytics.sentiment_breakdown.positive
  const neutral = analytics.sentiment_breakdown.neutral
  const negative = analytics.sentiment_breakdown.negative

  return (
    <div className="panel">
      <div className="section-header" style={{ marginTop: 0 }}>
        <div>
          <h3>Hype Score</h3>
          <p>Weighted from estimated trailer interaction, estimated search demand, social buzz, sentiment, and timing.</p>
        </div>
      </div>
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-label">Hype Score</div>
          <div className="metric-value">{analytics.hype_score}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Buzz Score</div>
          <div className="metric-value">{analytics.buzz_score}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Sentiment</div>
          <div className="metric-value">{Math.round(analytics.sentiment_score * 100)}%</div>
        </div>
      </div>
      <div style={{ marginTop: 20 }}>
        <p className="metric-label">Reaction Mix</p>
        <div className="genre-list" style={{ marginTop: 14 }}>
          <span className="genre-tag">Positive {positive}%</span>
          <span className="genre-tag">Neutral {neutral}%</span>
          <span className="genre-tag">Negative {negative}%</span>
        </div>
      </div>
    </div>
  )
}
