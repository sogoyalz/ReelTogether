'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ArrowDown, ArrowUpRight, ChevronLeft, ChevronRight, Users } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { movieApi, type MovieSummary } from '@/lib/api'
import { MovieArtwork } from '@/components/shared/MovieArtwork'

export function CinemaHero({ movies }: { movies?: MovieSummary[] }) {
  const [index, setIndex] = useState(0)
  const { data } = useQuery({ queryKey: ['trending-movies'], queryFn: () => movieApi.getTrending(), initialData: movies, enabled: !movies })
  const films = (data ?? []).slice(0, 4)
  const featured = films[index % Math.max(1, films.length)]
  return <section className="cinema-hero" aria-labelledby="home-title">
    <div className="cinema-hero-art" key={featured?.id ?? 'empty'}>{featured && <MovieArtwork src={featured.backdrop_url || featured.poster_url} title={featured.title} backdrop priority />}</div>
    <div className="cinema-hero-shade" />
    <div className="cinema-hero-content">
      <div className="hero-edition"><span className="live-dot" /> A PLACE FOR FILM PEOPLE <span className="edition-line" /></div>
      <h1 id="home-title">Great stories.<br /><em>Better together.</em></h1>
      <p className="cinema-hero-description">The next film you love is out there.<br />Find it. Save it. Make a night of it.</p>
      <div className="hero-actions"><Link href="/discover" className="cta-button">Find your next film <ArrowUpRight size={18} /></Link><Link href="/movie-night" className="text-action"><Users size={18} /> Start a movie night</Link></div>
      <div className="hero-footnote"><span className="mini-reels" aria-hidden="true"><i /><i /><i /></span><span>Different tastes. One great pick.</span></div>
    </div>
    <div className="hero-film-caption">
      {featured ? <><div className="caption-index"><span>IN THE SPOTLIGHT</span><span>{String(index % films.length + 1).padStart(2,'0')} / {String(films.length).padStart(2,'0')}</span></div><Link href={`/movies/${featured.slug}`} className="caption-film"><span><strong>{featured.title}</strong><small>{featured.release_date.slice(0,4)} · {featured.genres.slice(0,2).join(' / ') || 'Explore the film'}</small></span><ArrowUpRight size={23} /></Link>{films.length > 1 && <div className="hero-film-controls"><button aria-label="Previous featured film" onClick={() => setIndex((index + films.length - 1) % films.length)}><ChevronLeft size={18} /></button><div className="film-progress" aria-hidden="true">{films.map((film,i) => <span key={film.id} className={i===index % films.length ? 'active' : ''} />)}</div><button aria-label="Next featured film" onClick={() => setIndex((index + 1) % films.length)}><ChevronRight size={18} /></button></div>}{featured.field_sources?.title === 'generated' && <span className="hero-data-note">Demo catalog · illustrative artwork</span>}</> : <p className="meta">Your next discovery starts here.</p>}
    </div>
    <a href="#tonight" className="hero-scroll"><ArrowDown size={15} /><span>THE NIGHT STARTS HERE</span></a>
  </section>
}
