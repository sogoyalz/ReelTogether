'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { movieApi } from '@/lib/api'

import { ErrorState, LoadingState } from '../shared/QueryState'

export function HomeSignalOverview() {
  const [view, setView] = useState<'momentum' | 'catalog' | 'research'>('momentum')
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
  const cards = useMemo(() => {
    const updatedAt = new Date(dashboard.updated_at).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
    })

    if (view === 'catalog') {
      return [
        {
          label: 'Tracked Titles',
          value: String(dashboard.stats.tracked_movies),
          description: 'Titles active in the analytics catalog right now.',
        },
        {
          label: 'Average Hype',
          value: String(dashboard.stats.average_hype_score),
          description: 'Mean hype score across the tracked slate.',
        },
        {
          label: 'Average Buzz',
          value: String(dashboard.stats.average_buzz_score),
          description: `Live blended attention snapshot updated ${updatedAt}.`,
        },
      ]
    }

    if (view === 'research') {
      return [
        {
          label: 'Studio Trail',
          value: topTrending?.studios?.[0] || 'Open Studio',
          description: 'Jump from the loudest title into the company behind it.',
        },
        {
          label: 'Talent Trail',
          value: topTrending?.cast?.[0] || topTrending?.directors?.[0] || 'Open Talent',
          description: 'Follow the actor or director drawing the current conversation.',
        },
        {
          label: 'Franchise Trail',
          value: topHyped?.franchise || 'Standalone',
          description: 'Move from one title into the broader series context.',
        },
      ]
    }

    return [
      {
        label: 'Top Buzz Title',
        value: topTrending?.title || 'Unavailable',
        description: topTrending ? `Buzz ${topTrending.buzz_score} with hype ${topTrending.hype_score}.` : 'No trending title yet.',
      },
      {
        label: 'Top Hype Title',
        value: topHyped?.title || 'Unavailable',
        description: topHyped ? `Hype ${topHyped.hype_score} and status ${topHyped.status}.` : 'No hype leader yet.',
      },
      {
        label: 'Signal Refresh',
        value: updatedAt,
        description: 'Dashboard snapshot showing the latest homepage pulse.',
      },
    ]
  }, [dashboard, topHyped, topTrending, view])

  const quickLinks = [
    { href: '/search', label: 'Run research' },
    { href: '/discover', label: 'Open discovery' },
    { href: '/compare', label: 'Compare titles' },
  ]

  return (
    <div className="hero-grid">
      <div className="panel hero-signal-panel">
        <div className="section-header" style={{ marginTop: 0, marginBottom: 14 }}>
          <div>
            <p className="metric-label">Signal Stack</p>
            <p className="meta">Switch the lens to browse the homepage like a working product surface.</p>
          </div>
        </div>
        <div className="interactive-toggle-row">
          {[
            ['momentum', 'Momentum'],
            ['catalog', 'Catalog'],
            ['research', 'Research'],
          ].map(([key, label]) => (
            <button
              className={view === key ? 'interactive-toggle interactive-toggle-active' : 'interactive-toggle'}
              key={key}
              onClick={() => setView(key as 'momentum' | 'catalog' | 'research')}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
        <div className="genre-list" style={{ marginTop: 16 }}>
          {(view === 'research'
            ? ['Studios', 'Talent routes', 'Franchise links', 'Semantic search', 'Movie detail drilldown', 'Compare workflow']
            : ['Trailer momentum', 'Search demand', 'Social chatter', 'Streaming context', 'Ratings overlays', 'Box office trajectory']
          ).map((item) => (
            <span className="genre-tag" key={item}>
              {item}
            </span>
          ))}
        </div>
        <div className="overview-grid" style={{ marginTop: 20 }}>
          {cards.map((card) => (
            <div className="metric-card interactive-card" key={card.label}>
              <div className="metric-label">{card.label}</div>
              <div className="metric-value overview-title">{card.value}</div>
              <p className="meta">{card.description}</p>
            </div>
          ))}
        </div>
        <div className="hero-actions" style={{ marginTop: 18 }}>
          {quickLinks.map((link) => (
            <Link className="cta-button secondary-button interactive-link-button" href={link.href} key={link.href}>
              {link.label}
            </Link>
          ))}
        </div>
      </div>
      <div className="hero-stat-rail">
        <Link className="metric-card hero-stat-card interactive-stat-card" href={topTrending ? `/movies/${topTrending.slug}` : '/movies'}>
          <div className="metric-label">Live Leader</div>
          <div className="metric-value">{topTrending?.buzz_score ?? dashboard.stats.average_buzz_score}</div>
          <p className="meta">{topTrending ? `${topTrending.title} is driving the current buzz board.` : 'Browse the strongest current title.'}</p>
        </Link>
        <Link className="metric-card hero-stat-card interactive-stat-card" href={topHyped?.franchise ? `/franchises/${encodeURIComponent(topHyped.franchise)}` : '/discover'}>
          <div className="metric-label">Hype Trail</div>
          <div className="metric-value">{topHyped?.hype_score ?? dashboard.stats.average_hype_score}</div>
          <p className="meta">{topHyped?.franchise ? `${topHyped.franchise} is the strongest series signal.` : 'Open discovery to inspect hype clusters.'}</p>
        </Link>
        <Link className="metric-card hero-stat-card interactive-stat-card" href="/search">
          <div className="metric-label">Research Prompt</div>
          <div className="metric-value">{dashboard.stats.tracked_movies}</div>
          <p className="meta">Use the search surface to move from title to studio, people, and franchise routes.</p>
        </Link>
      </div>
    </div>
  )
}
