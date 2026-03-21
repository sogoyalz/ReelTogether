'use client'

import { useQuery } from '@tanstack/react-query'

import { movieApi } from '@/lib/api'

import { ErrorState, LoadingState } from '../shared/QueryState'

export function HomeSignalOverview() {
  const dashboardQuery = useQuery({
    queryKey: ['home-dashboard'],
    queryFn: movieApi.getDashboard,
  })

  if (dashboardQuery.isLoading) {
    return (
      <div className="hero-grid">
        <LoadingState title="Loading signal overview" description="Building the latest homepage analytics snapshot." />
        <LoadingState title="Loading market snapshot" description="Summarizing the tracked catalog and active compare surface." />
      </div>
    )
  }

  if (dashboardQuery.isError || !dashboardQuery.data) {
    return (
      <div className="hero-grid">
        <ErrorState title="Homepage signal unavailable" description="The dashboard feed did not load." />
        <ErrorState title="Catalog snapshot unavailable" description="Tracked metrics could not be summarized right now." />
      </div>
    )
  }

  const dashboard = dashboardQuery.data
  const topTrending = dashboard.trending[0]
  const topHyped = dashboard.most_hyped[0]

  return (
    <div className="hero-grid">
      <div className="panel hero-signal-panel">
        <p className="metric-label">Signal Stack</p>
        <div className="genre-list" style={{ marginTop: 16 }}>
          {['Trailer momentum', 'Search demand', 'Social chatter', 'Streaming context', 'Ratings overlays', 'Box office trajectory'].map(
            (item) => (
              <span className="genre-tag" key={item}>
                {item}
              </span>
            ),
          )}
        </div>
        <div className="overview-grid" style={{ marginTop: 20 }}>
          <div className="metric-card">
            <div className="metric-label">Top Buzz Title</div>
            <div className="metric-value overview-title">{topTrending?.title || 'Unavailable'}</div>
            <p className="meta">
              {topTrending ? `Buzz ${topTrending.buzz_score} • Hype ${topTrending.hype_score}` : 'No trending title yet.'}
            </p>
          </div>
          <div className="metric-card">
            <div className="metric-label">Top Hype Title</div>
            <div className="metric-value overview-title">{topHyped?.title || 'Unavailable'}</div>
            <p className="meta">
              {topHyped ? `Hype ${topHyped.hype_score} • ${topHyped.status}` : 'No hype leader yet.'}
            </p>
          </div>
        </div>
      </div>
      <div className="hero-stat-rail">
        <div className="metric-card hero-stat-card">
          <div className="metric-label">Tracked Titles</div>
          <div className="metric-value">{dashboard.stats.tracked_movies}</div>
          <p className="meta">Titles currently active in the analytics catalog.</p>
        </div>
        <div className="metric-card hero-stat-card">
          <div className="metric-label">Average Hype</div>
          <div className="metric-value">{dashboard.stats.average_hype_score}</div>
          <p className="meta">Average hype score across the full tracked slate.</p>
        </div>
        <div className="metric-card hero-stat-card">
          <div className="metric-label">Average Buzz</div>
          <div className="metric-value">{dashboard.stats.average_buzz_score}</div>
          <p className="meta">Current blended attention score across the catalog.</p>
        </div>
      </div>
    </div>
  )
}
