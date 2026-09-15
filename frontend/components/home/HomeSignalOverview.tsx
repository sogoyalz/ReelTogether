'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'

import { movieApi, type DashboardResponse } from '@/lib/api'

import { ErrorState, LoadingState } from '../shared/QueryState'

export function HomeSignalOverview({ dashboard: initialDashboard }: { dashboard?: DashboardResponse }) {
  const dashboardQuery = useQuery({
    queryKey: ['dashboard'],
    queryFn: movieApi.getDashboard,
    initialData: initialDashboard,
  })

  if (dashboardQuery.isLoading) {
    return <LoadingState title="Loading overview" description="Fetching homepage stats." />
  }

  if (dashboardQuery.isError || !dashboardQuery.data) {
    return <ErrorState title="Overview unavailable" description="The homepage dashboard could not be loaded." />
  }

  const dashboard = dashboardQuery.data
  return <div className="home-catalog-snapshot">
    <div><strong>{dashboard.stats.tracked_movies.toLocaleString()}</strong><span>movies to explore</span></div>
    <div><strong>{dashboard.stats.average_hype_score}</strong><span>average catalog hype</span></div>
    <div><strong>{dashboard.stats.average_buzz_score}</strong><span>average catalog buzz</span></div>
    <p>Explore the stories behind the scores.<small>Attention scores can include estimates.</small><Link href="/movies">Browse the library ↗</Link></p>
  </div>
}
