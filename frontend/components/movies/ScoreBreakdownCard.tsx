import type { MovieAnalytics } from '@/lib/api'

export function ScoreBreakdownCard({ analytics }: { analytics: MovieAnalytics }) {
  const entries = [
    ['Trailer Interest', analytics.score_breakdown.youtube_interest],
    ['Search Demand', analytics.score_breakdown.search_interest],
    ['Social Buzz', analytics.score_breakdown.social_buzz],
    ['Sentiment', analytics.score_breakdown.sentiment],
    ['Momentum', analytics.score_breakdown.momentum],
    ['Release Timing', analytics.score_breakdown.release_proximity],
  ] as const

  return (
    <div className="panel">
      <div className="section-header" style={{ marginTop: 0 }}>
        <div>
          <h3>Score Breakdown</h3>
          <p>Transparent component view behind the current hype score.</p>
        </div>
      </div>
      <div className="stack">
        {entries.map(([label, value]) => (
          <div className="breakdown-row" key={label}>
            <div className="metric-label">{label}</div>
            <div className="breakdown-bar">
              <span style={{ width: `${Math.round(value * 100)}%` }} />
            </div>
            <div>{Math.round(value * 100)}%</div>
          </div>
        ))}
      </div>
    </div>
  )
}
