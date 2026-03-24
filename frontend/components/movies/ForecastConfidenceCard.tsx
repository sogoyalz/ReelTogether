import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { MovieAIOverview } from '@/lib/api'
import { formatCurrency } from '@/lib/formatters'

export function ForecastConfidenceCard({ ai }: { ai: MovieAIOverview }) {
  const featureData = ai.prediction.feature_importance.map((item) => ({
    label: item.label,
    impact: Math.round(item.impact_score * 100),
  }))

  return (
    <div className="panel">
      <div className="section-header" style={{ marginTop: 0 }}>
        <div>
          <h3>Forecast Confidence</h3>
          <p>Projection ranges and feature-importance view behind the current box office model.</p>
        </div>
      </div>

      <div className="stack">
        <div className="overview-grid">
          <div className="metric-card">
            <div className="metric-label">Opening Range</div>
            <div className="metric-value overview-title">
              {formatCurrency(ai.prediction.opening_weekend_low_usd)} - {formatCurrency(ai.prediction.opening_weekend_high_usd)}
            </div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Domestic Range</div>
            <div className="metric-value overview-title">
              {formatCurrency(ai.prediction.domestic_total_low_usd)} - {formatCurrency(ai.prediction.domestic_total_high_usd)}
            </div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Confidence</div>
            <div className="metric-value overview-title">{Math.round(ai.prediction.confidence_score * 100)}%</div>
            <p className="meta">{ai.prediction.model_version}</p>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Methodology</div>
          <p className="subtle" style={{ marginTop: 10 }}>{ai.prediction.methodology}</p>
        </div>

        <div className="metric-card">
          <div className="metric-label">Feature Importance</div>
          <div className="chart-shell" style={{ height: 280, marginTop: 16 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={featureData} layout="vertical" margin={{ left: 20, right: 20, top: 8, bottom: 8 }}>
                <CartesianGrid stroke="rgba(255,255,255,0.08)" horizontal={false} />
                <XAxis type="number" tick={{ fill: '#9aa8ba' }} unit="%" />
                <YAxis dataKey="label" type="category" tick={{ fill: '#d7deeb' }} width={110} />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(18, 18, 18, 0.96)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: 16,
                  }}
                />
                <Bar dataKey="impact" fill="url(#forecastGradient)" radius={[0, 12, 12, 0]} />
                <defs>
                  <linearGradient id="forecastGradient" x1="0" x2="1">
                    <stop offset="0%" stopColor="#f1f1f1" />
                    <stop offset="100%" stopColor="#8c8c8c" />
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}
