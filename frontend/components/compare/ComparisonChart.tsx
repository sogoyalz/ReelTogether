'use client'

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { ComparisonItem } from '@/lib/api'

export function ComparisonChart({ items }: { items: ComparisonItem[] }) {
  return (
    <div className="panel">
      <div className="section-header" style={{ marginTop: 0 }}>
        <div>
          <h3>Hype vs Buzz</h3>
          <p>Visual side-by-side ranking for the selected titles and their overall momentum.</p>
        </div>
      </div>
      <div className="chart-shell">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={items}>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
            <XAxis dataKey="title" stroke="#98a2b3" />
            <YAxis stroke="#98a2b3" />
            <Tooltip />
            <Legend />
            <Bar dataKey="buzz_score" fill="#ff8e3c" radius={[8, 8, 0, 0]} />
            <Bar dataKey="hype_score" fill="#4ea1ff" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
