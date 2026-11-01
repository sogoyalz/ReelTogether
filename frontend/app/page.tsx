import Link from 'next/link'
import { ArrowUpRight, Check, Users } from 'lucide-react'
import { CinemaHero } from '@/components/home/CinemaHero'
import { TrendingMovies } from '@/components/home/TrendingMovies'
import { ReleasedMovies } from '@/components/home/ReleasedMovies'
import { UpcomingMovies } from '@/components/home/UpcomingMovies'
import { HomeSignalOverview } from '@/components/home/HomeSignalOverview'
import { BuzzRanking } from '@/components/home/BuzzRanking'
import { MovieArtwork } from '@/components/shared/MovieArtwork'
import { SectionHeading } from '@/components/shared/SectionHeading'
import { Reveal } from '@/components/shared/Reveal'
import { SearchBar } from '@/components/shared/SearchBar'
import { getHomePagePayload } from '@/lib/server-api'

export const dynamic = 'force-dynamic'
const pathways = [
  { genre:'Science Fiction', title:'Somewhere beyond here.', label:'OTHER WORLDS', symbol:'◌' },
  { genre:'Thriller', title:'One more plot twist.', label:'ON THE EDGE', symbol:'↗' },
  { genre:'Animation', title:'A little more wonder.', label:'NEW PERSPECTIVES', symbol:'✳' },
  { genre:'Drama', title:'Stay for the feeling.', label:'HUMAN STORIES', symbol:'◎' },
]

export default async function Home() {
  const homepage = await getHomePagePayload()
  const socialArt = homepage?.released?.[0] ?? homepage?.trending?.[1]
  return <main className="home-page">
    <CinemaHero movies={homepage?.trending} />
    <div className="home-content">
      <section className="discovery-search" aria-label="Find a movie"><div><span className="eyebrow">HAVE SOMETHING IN MIND?</span><h2>Follow your curiosity.</h2></div><SearchBar /></section>
      <section id="tonight" className="home-chapter"><Reveal><SectionHeading number="01" eyebrow="THE CONVERSATION STARTERS" title="On everyone’s radar." description="Films drawing attention in the current catalog. Your next discovery, perhaps." href="/movies" action="Explore the library" /><TrendingMovies movies={homepage?.trending} /></Reveal></section>
      <Reveal><section className="social-cinema" aria-labelledby="social-title"><div className="social-art">{socialArt && <MovieArtwork src={socialArt.backdrop_url || socialArt.poster_url} title={socialArt.title} backdrop />}<div className="social-art-shade" /><span className="social-screen-label">PRESENTING: YOUR NEXT MOVIE NIGHT</span><div className="social-ballot" aria-hidden="true"><span className="ballot-dot"><Check size={15} /></span><span>A film everyone’s into.</span><Users size={19} /></div><span className="social-film-label">{socialArt?.title ?? 'The best seat is together.'}</span></div><div className="social-copy"><span className="eyebrow"><span className="section-number">02</span> LESS GROUP-CHAT DEBATE</span><h2>Your people.<br />Your <em>kind of cinema.</em></h2><p>You bring the different tastes. We’ll help find the common ground.</p><ol className="night-process"><li><span>01</span>Invite your circle<small>A private room for 2–8 friends.</small></li><li><span>02</span>Make your picks<small>Vote privately. No pressure.</small></li><li><span>03</span>Let the night begin<small>Reveal the matches and choose together.</small></li></ol><Link className="cta-button" href="/movie-night">Make it a movie night <ArrowUpRight size={18} /></Link></div></section></Reveal>
      <section className="home-chapter"><Reveal><SectionHeading number="03" eyebrow="FOLLOW A DIFFERENT THREAD" title="What world are you in?" description="No mood-reading algorithms. Just a good place to start." /><div className="genre-pathways">{pathways.map((path,i) => <Link className={`genre-pathway genre-pathway-${i}`} href={`/genres/${encodeURIComponent(path.genre)}`} key={path.genre}><span className="genre-path-top">{path.label}<ArrowUpRight size={16}/></span><span className="genre-symbol" aria-hidden="true">{path.symbol}</span><h3>{path.title}</h3><span className="genre-name">{path.genre}</span></Link>)}</div></Reveal></section>
      <section className="home-chapter upcoming-chapter"><Reveal><SectionHeading number="04" eyebrow="THE NEXT CHAPTER" title="Worth the wait." description="Upcoming titles to keep on your horizon." href="/upcoming" action="See what’s coming" /><UpcomingMovies movies={homepage?.upcoming} /></Reveal></section>
      <section className="home-chapter"><Reveal><SectionHeading number="05" eyebrow="THE CREDITS ROLLED. THE FEELING STAYED." title="Still thinking about it." description="Released films to discover, revisit and save for later." href="/movies" action="Find your next watch" /><ReleasedMovies movies={homepage?.released} /></Reveal></section>
      <details className="cinema-details catalog-notes"><summary>Behind the selection <span>Catalog coverage, source notes &amp; attention scores</span></summary><HomeSignalOverview dashboard={homepage?.dashboard} /><BuzzRanking dashboard={homepage?.dashboard} /></details>
    </div>
  </main>
}
