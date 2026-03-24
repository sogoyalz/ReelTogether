'use client'

import { Line, LineChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { AnalyticsHistoryResponse } from '@/lib/api'
import { formatCompactNumber } from '@/lib/formatters'

export function TrendChart({ history }: { history: AnalyticsHistoryResponse }) {
  return (
    <div className="panel">
      <div className="section-header" style={{ marginTop: 0 }}>
        <div>
          <h3>Momentum Over Time</h3>
          <p>Trend view across hype, buzz, search demand, and trailer reach.</p>
        </div>
      </div>
      <div className="chart-shell">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={history.points}>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
            <XAxis dataKey="snapshot_date" stroke="#98a2b3" />
            <YAxis stroke="#98a2b3" />
            <Tooltip formatter={(value: number) => formatCompactNumber(value)} />
            <Line type="monotone" dataKey="hype_score" stroke="#f1f1f1" strokeWidth={3} dot={false} />
            <Line type="monotone" dataKey="buzz_score" stroke="#bcbcbc" strokeWidth={3} dot={false} />
            <Line type="monotone" dataKey="google_trends_score" stroke="#7f7f7f" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
