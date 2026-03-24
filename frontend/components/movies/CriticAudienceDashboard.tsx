import type { MovieAIOverview } from '@/lib/api'

export function CriticAudienceDashboard({ ai }: { ai: MovieAIOverview }) {
  const comparison = ai.critic_vs_audience

  return (
    <div className="panel">
      <div className="section-header" style={{ marginTop: 0 }}>
        <div>
          <h3>Critic vs Audience</h3>
          <p>Side-by-side breakdown of what professional reviewers and normal viewers are emphasizing.</p>
        </div>
      </div>

      <div className="compare-grid">
        <PerspectiveCard
          description={comparison.critics.summary}
          itemCount={comparison.critics.item_count}
          label="Critics"
          negativeDrivers={comparison.critics.negative_drivers}
          positiveDrivers={comparison.critics.positive_drivers}
          sentimentScore={comparison.critics.sentiment_score}
          topThemes={comparison.critics.top_themes}
        />
        <PerspectiveCard
          description={comparison.audience.summary}
          itemCount={comparison.audience.item_count}
          label="Audience"
          negativeDrivers={comparison.audience.negative_drivers}
          positiveDrivers={comparison.audience.positive_drivers}
          sentimentScore={comparison.audience.sentiment_score}
          topThemes={comparison.audience.top_themes}
        />
      </div>

      <div className="stack" style={{ marginTop: 18 }}>
        <div className="metric-card">
          <div className="metric-label">Alignment Score</div>
          <div className="metric-value overview-title">{Math.round(comparison.alignment_score * 100)}%</div>
          <p className="meta">
            Consensus themes: {comparison.consensus_themes.length ? comparison.consensus_themes.join(', ') : 'Limited overlap'}
          </p>
        </div>
        {comparison.theme_signals.length ? (
          <div className="stack">
            {comparison.theme_signals.map((signal) => (
              <div className="metric-card" key={signal.theme}>
                <div className="title-row">
                  <div>
                    <div className="metric-label">{signal.theme}</div>
                    <p className="subtle" style={{ marginTop: 8 }}>
                      Critics {Math.round(signal.critic_weight * 100)}% vs audience {Math.round(signal.audience_weight * 100)}%
                    </p>
                  </div>
                  <div className="score-pill">{Math.round(signal.gap * 100)}%</div>
                </div>
                <div className="compare-stat-grid" style={{ marginTop: 14 }}>
                  <div>
                    <div className="metric-label">Critic Weight</div>
                    <div>{Math.round(signal.critic_weight * 100)}%</div>
                  </div>
                  <div>
                    <div className="metric-label">Audience Weight</div>
                    <div>{Math.round(signal.audience_weight * 100)}%</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  )
}

function PerspectiveCard({
  label,
  description,
  sentimentScore,
  itemCount,
  topThemes,
  positiveDrivers,
  negativeDrivers,
}: {
  label: string
  description: string
  sentimentScore: number
  itemCount: number
  topThemes: string[]
  positiveDrivers: string[]
  negativeDrivers: string[]
}) {
  return (
    <div className="metric-card">
      <div className="title-row">
        <div>
          <div className="metric-label">{label}</div>
          <p className="subtle" style={{ marginTop: 10 }}>{description}</p>
        </div>
        <div className="score-pill">{Math.round(((sentimentScore + 1) / 2) * 100)}%</div>
      </div>
      <p className="meta" style={{ marginTop: 12 }}>{itemCount} tracked items</p>
      {topThemes.length ? (
        <div className="genre-list">
          {topThemes.map((theme) => (
            <span className="genre-tag" key={`${label}-${theme}`}>{theme}</span>
          ))}
        </div>
      ) : null}
      <div className="compare-stat-grid">
        <div>
          <div className="metric-label">Positive Drivers</div>
          <div>{positiveDrivers.length ? positiveDrivers.join(', ') : 'n/a'}</div>
        </div>
        <div>
          <div className="metric-label">Negative Drivers</div>
          <div>{negativeDrivers.length ? negativeDrivers.join(', ') : 'n/a'}</div>
        </div>
      </div>
    </div>
  )
}
