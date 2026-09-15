import type { MovieAIOverview } from '@/lib/api'

export function ForecastConfidenceCard({ ai }: { ai: MovieAIOverview }) {
  return <section className="panel">
    <h3>Forecast methodology</h3>
    <p className="subtle">{ai.prediction.methodology}</p>
    <p className="meta">This experimental estimate has no validated accuracy, confidence interval, or measured feature importance. It should not be used for financial decisions.</p>
  </section>
}
