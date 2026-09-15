'use client'

import {
  Bar,
  ComposedChart,
  CartesianGrid,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { SentimentTimelineResponse } from '@/lib/api'

function formatWeekLabel(value: string) {
  return new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function trendLabel(trend: SentimentTimelineResponse['sentiment_trend']) {
  if (trend === 'improving') {
    return 'Sentiment improving over time'
  }
  if (trend === 'declining') {
    return 'Sentiment declining over time'
  }
  return 'Sentiment stable over time'
}

export function SentimentTimeline({ payload }: { payload: SentimentTimelineResponse }) {
  if (payload.timeline.length < 3) {
    return (
      <div className="panel">
        <div className="section-header" style={{ marginTop: 0 }}>
          <div>
            <h3>Sentiment Timeline</h3>
            <p>Not enough reviews yet to show a timeline.</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="panel">
      <div className="section-header" style={{ marginTop: 0 }}>
        <div>
          <h3>Sentiment Timeline</h3>
          <p>Weekly review sentiment after release, with volume in the background.</p>
        </div>
      </div>

      <div className="hero-actions" style={{ marginTop: 0, marginBottom: 18 }}>
        <span className="genre-tag">😊 {payload.positive_pct}% Positive</span>
        <span className="genre-tag">😐 {payload.neutral_pct}% Neutral</span>
        <span className="genre-tag">😤 {payload.negative_pct}% Negative</span>
      </div>

      <div className="chart-shell">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={payload.timeline}>
            <defs>
              <linearGradient id="sentimentStroke" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#22c55e" />
                <stop offset="50%" stopColor="#e5e7eb" />
                <stop offset="100%" stopColor="#ef4444" />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
            <XAxis dataKey="week" stroke="#98a2b3" tickFormatter={formatWeekLabel} />
            <YAxis domain={[-1, 1]} stroke="#98a2b3" yAxisId="sentiment" />
            <YAxis allowDecimals={false} orientation="right" stroke="#98a2b3" yAxisId="volume" />
            <Tooltip
              formatter={(value: number, name: string) => {
                if (name === 'avg_sentiment') {
                  return [value.toFixed(2), 'Avg sentiment']
                }
                if (name === 'review_count') {
                  return [value, 'Review count']
                }
                return [value, name]
              }}
              labelFormatter={(label) => formatWeekLabel(label)}
            />
            <ReferenceLine stroke="rgba(255,255,255,0.2)" y={0} yAxisId="sentiment" />
            <Bar dataKey="review_count" fill="rgba(255,255,255,0.16)" radius={[8, 8, 0, 0]} yAxisId="volume" />
            <Line
              dataKey="avg_sentiment"
              dot={{ fill: '#ffffff', r: 3 }}
              stroke="url(#sentimentStroke)"
              strokeWidth={3}
              type="monotone"
              yAxisId="sentiment"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div style={{ marginTop: 16 }}>
        <span className="inline-chip">
          {payload.sentiment_trend === 'improving'
            ? `📈 ${trendLabel(payload.sentiment_trend)}`
            : payload.sentiment_trend === 'declining'
              ? `📉 ${trendLabel(payload.sentiment_trend)}`
              : `➡️ ${trendLabel(payload.sentiment_trend)}`}
        </span>
      </div>
    </div>
  )
}
