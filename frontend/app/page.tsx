import Link from 'next/link'

import { BuzzRanking } from '@/components/home/BuzzRanking'
import { HomeSignalOverview } from '@/components/home/HomeSignalOverview'
import { ReleasedMovies } from '@/components/home/ReleasedMovies'
import { TrendingMovies } from '@/components/home/TrendingMovies'
import { UpcomingMovies } from '@/components/home/UpcomingMovies'
import { SearchBar } from '@/components/shared/SearchBar'

export default function Home() {
  return (
    <main className="page-shell">
      <section className="hero-panel hero-panel-immersive">
        <div className="hero-copy-stack">
          <span className="eyebrow">Movie Pulse Analytics</span>
          <h1 className="hero-title">A sharper, more cinematic way to browse movie momentum.</h1>
          <p className="hero-copy">
            Search titles instantly, move through franchises and genres, compare contenders,
            and read the audience signal behind every movie in a cleaner editorial interface.
          </p>
          <div style={{ marginTop: 24 }}>
            <SearchBar />
          </div>
          <div className="hero-actions" style={{ marginTop: 22 }}>
            <Link className="cta-button" href="/compare">
              Compare movies
            </Link>
            <Link className="cta-button secondary-button" href="/movies">
              Browse library
            </Link>
            <Link className="cta-button secondary-button" href="/discover">
              Open discovery
            </Link>
          </div>
        </div>

        <HomeSignalOverview />
      </section>

      <div className="section-header">
        <div>
          <h2>Trending Movies</h2>
          <p>Titles getting the strongest current attention signals.</p>
        </div>
      </div>
      <TrendingMovies />

      <div className="section-header">
        <div>
          <h2>Upcoming Releases</h2>
          <p>The release calendar with early audience demand built in.</p>
        </div>
        <Link className="eyebrow" href="/upcoming">
          See all upcoming
        </Link>
      </div>
      <UpcomingMovies />

      <div className="section-header">
        <div>
          <h2>Released Movies</h2>
          <p>Older releases with the same detail pages, scores, and trailer metrics.</p>
        </div>
      </div>
      <ReleasedMovies />

      <div className="section-header">
        <div>
          <h2>Buzz Score Ranking</h2>
          <p>A fast leaderboard for movie lovers who want signal over noise.</p>
        </div>
      </div>
      <BuzzRanking />
    </main>
  )
}
