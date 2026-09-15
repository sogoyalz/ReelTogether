import Link from 'next/link'
import { ArrowUpRight, Sparkles } from 'lucide-react'
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
          <span className="cinema-kicker">MOVIE DISCOVERY, PERSONALIZED</span>
          <h1>Discover your<br />next favourite film<span>.</span></h1>
          <p>Explore the catalog, compare films, and get recommendations tailored to your preferences.</p>
          <div className="hero-actions">
            <Link className="cta-button" href="/recommendations"><Sparkles size={17} /> Find my next movie</Link>
            <Link className="cinema-secondary" href="/movies">Explore the library <ArrowUpRight size={17} /></Link>
          </div>
        </div>
        {featured && <Link className="home-featured-caption" href={`/movies/${featured.slug}`}><span>IN THE SPOTLIGHT</span><strong>{featured.title} <ArrowUpRight size={16} /></strong></Link>}
      </section>
      <section className="home-search-strip" aria-label="Find a movie"><div><strong>Have a movie in mind?</strong><p className="meta">Search the catalog and start exploring.</p></div><SearchBar /></section>

      <section style={{ marginTop: 24 }}>
        <HomeSignalOverview dashboard={homepage?.dashboard} />
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

      <div className="section-header">
        <div>
          <h2>Buzz Score Ranking</h2>
          <p>Compare the catalog’s attention scores. Some signals are estimates.</p>
        </div>
      </div>
      <BuzzRanking dashboard={homepage?.dashboard} />
    </main>
  )
}
