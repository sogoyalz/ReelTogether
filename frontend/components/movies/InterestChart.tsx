'use client'

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { MovieAnalytics } from '@/lib/api'
import { formatCompactNumber } from '@/lib/formatters'

export function InterestChart({ analytics }: { analytics: MovieAnalytics }) {
  const data = [
    { name: 'Trailer Views', value: analytics.youtube_views },
    { name: 'Social Mentions', value: analytics.social_mentions },
    { name: 'Google Trends', value: analytics.google_trends_score * 1000000 },
    { name: 'Opening Weekend', value: analytics.predicted_opening_weekend_usd },
  ]

  return (
    <div className="panel">
      <div className="section-header" style={{ marginTop: 0 }}>
        <div>
          <h3>Interest Snapshot</h3>
          <p>Scaled comparison of audience attention and commercial potential.</p>
        </div>
      </div>
      <div className="chart-shell">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
            <XAxis dataKey="name" stroke="#98a2b3" />
            <YAxis stroke="#98a2b3" tickFormatter={formatCompactNumber} />
            <Tooltip formatter={(value: number) => formatCompactNumber(value)} />
            <Bar dataKey="value" fill="#ff8e3c" radius={[10, 10, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
