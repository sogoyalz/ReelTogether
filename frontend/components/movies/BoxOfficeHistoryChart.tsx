'use client'

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { MovieDetail } from '@/lib/api'
import { formatCurrency } from '@/lib/formatters'

export function BoxOfficeHistoryChart({ movie }: { movie: MovieDetail }) {
  if (!movie.box_office_history.length) {
    return null
  }

  return (
    <div className="panel">
      <div className="section-header" style={{ marginTop: 0 }}>
        <div>
          <h3>Box Office Track</h3>
          <p>Compact box office trajectory from forecast/opening to domestic finish.</p>
        </div>
      </div>
      <div className="chart-shell">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={movie.box_office_history}>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
            <XAxis dataKey="label" stroke="#98a2b3" />
            <YAxis stroke="#98a2b3" tickFormatter={formatCurrency} />
            <Tooltip formatter={(value: number) => formatCurrency(value)} />
            <Area dataKey="value_usd" stroke="#f1f1f1" fill="rgba(255,255,255,0.22)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
