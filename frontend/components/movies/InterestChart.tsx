import type { MovieAnalytics } from '@/lib/api'
import { formatCompactNumber } from '@/lib/formatters'

export function InterestChart({ analytics }: { analytics: MovieAnalytics }) {
  return <section className="panel">
    <h3>Interest snapshot</h3>
    <p className="subtle">These signals use different units and are shown separately. Attention figures may be estimated.</p>
    <dl className="overview-grid">
      <div><dt>Trailer views</dt><dd>{formatCompactNumber(analytics.youtube_views)}</dd></div>
      <div><dt>Social mentions</dt><dd>{formatCompactNumber(analytics.social_mentions)}</dd></div>
      <div><dt>Search demand estimate (0–100)</dt><dd>{analytics.google_trends_score}</dd></div>
    </dl>
  </section>
}
