'use client'

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { ComparisonItem } from '@/lib/api'

export function ComparisonChart({ items }: { items: ComparisonItem[] }) {
  const chartData = items.map((item) => ({
    title: item.title,
    buzz: item.buzz_score,
    hype: item.hype_score,
    search: item.google_trends_score,
    popularity: Math.round(item.tmdb_popularity),
  }))

  return (
    <div className="panel">
      <div className="section-header" style={{ marginTop: 0 }}>
        <div>
          <h3>Buzz, Hype, Search, Popularity</h3>
          <p>Visual side-by-side ranking for the selected titles across the main research signals.</p>
        </div>
      </div>
      <div className="chart-shell">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
            <XAxis dataKey="title" stroke="#98a2b3" />
            <YAxis stroke="#98a2b3" />
            <Tooltip />
            <Legend />
            <Bar dataKey="buzz" fill="#efefef" radius={[8, 8, 0, 0]} />
            <Bar dataKey="hype" fill="#c9c9c9" radius={[8, 8, 0, 0]} />
            <Bar dataKey="search" fill="#9d9d9d" radius={[8, 8, 0, 0]} />
            <Bar dataKey="popularity" fill="#6f6f6f" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
