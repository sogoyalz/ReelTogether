import Link from 'next/link'
import { ArrowUpRight, Sparkles, Users } from 'lucide-react'
import { MovieArtwork } from '@/components/shared/MovieArtwork'

import { BuzzRanking } from '@/components/home/BuzzRanking'
import { HomeSignalOverview } from '@/components/home/HomeSignalOverview'
import { ReleasedMovies } from '@/components/home/ReleasedMovies'
import { TrendingMovies } from '@/components/home/TrendingMovies'
import { UpcomingMovies } from '@/components/home/UpcomingMovies'
import { SearchBar } from '@/components/shared/SearchBar'
import { getHomePagePayload } from '@/lib/server-api'

export const dynamic = 'force-dynamic'

export default async function Home() {
  const homepage = await getHomePagePayload()
  const featured = homepage?.trending?.[0]

  return (
    <main className="page-shell">
      <section className="home-cinema-hero">
        {featured && <MovieArtwork src={featured.backdrop_url || featured.poster_url} title={featured.title} backdrop />}
        <div className="home-cinema-copy">
          <span className="cinema-kicker">LESS SCROLLING. MORE CINEMA.</span>
          <h1>Your next great<br />movie night<span>.</span></h1>
          <p>Find a film that feels like you. Or bring your friends and choose something together.</p>
          <div className="hero-actions">
            <Link className="cta-button" href="/discover"><Sparkles size={17} /> Discover a film</Link>
            <Link className="cinema-secondary" href="/movie-night">Plan a movie night <ArrowUpRight size={17} /></Link>
          </div>
        </div>
        {featured && <Link className="home-featured-caption" href={`/movies/${featured.slug}`}><span>IN THE SPOTLIGHT</span><strong>{featured.title} <ArrowUpRight size={16} /></strong></Link>}
      </section>
      <section className="home-search-strip" aria-label="Find a movie"><div><strong>Have a movie in mind?</strong><p className="meta">Search the catalog and start exploring.</p></div><SearchBar /></section>

      <section className="together-feature" aria-labelledby="together-title">
        <span className="together-icon"><Users size={25} aria-hidden="true" /></span>
        <div><span className="cinema-kicker">BETTER TOGETHER</span><h2 id="together-title">Different tastes. One great movie.</h2><p>Invite your friends, share your picks, and find your next watch together.</p></div>
        <Link className="cta-button secondary-button" href="/movie-night">Start a movie night <ArrowUpRight size={16} /></Link>
      </section>

      <div className="section-header">
        <div>
          <h2>Trending Movies</h2>
          <p>Explore titles ranked by the catalog’s attention scores.</p>
        </div>
      </div>
      <TrendingMovies movies={homepage?.trending} />

      <div className="section-header">
        <div>
          <h2>Upcoming Releases</h2>
          <p>Something to look forward to. Explore upcoming releases.</p>
        </div>
        <Link className="eyebrow" href="/upcoming">
          See all upcoming
        </Link>
      </div>
      <UpcomingMovies movies={homepage?.upcoming} />

      <div className="section-header">
        <div>
          <h2>Released Movies</h2>
          <p>Find a favourite you missed—or revisit one you love.</p>
        </div>
      </div>
      <ReleasedMovies movies={homepage?.released} />

      <details className="cinema-details"><summary>Behind the picks <span>Catalog coverage &amp; attention scores</span></summary>
      <HomeSignalOverview dashboard={homepage?.dashboard} />
      <div className="section-header">
        <div>
          <h2>Buzz Score Ranking</h2>
          <p>Compare the catalog’s attention scores. Some signals are estimates.</p>
        </div>
      </div>
      <BuzzRanking dashboard={homepage?.dashboard} />
      </details>
    </main>
  )
}
