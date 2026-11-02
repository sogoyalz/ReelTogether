'use client'

import Link from 'next/link'
import { ArrowUpRight } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { MovieCard } from '@/components/shared/MovieCard'
import { SectionHeading } from '@/components/shared/SectionHeading'
import { Reveal } from '@/components/shared/Reveal'
import { ErrorState, LoadingState } from '@/components/shared/QueryState'
import { movieApi } from '@/lib/api'

export default function DiscoverPage() {
  const query = useQuery({ queryKey:['discovery-dashboard'], queryFn:movieApi.getDiscoveryDashboard })
  const dashboard = query.data
  const collections = Object.entries(dashboard?.editorial_collections ?? {})
  const formatLabel = (text:string) => text.split('_').map(word=>word.charAt(0).toUpperCase()+word.slice(1)).join(' ')
  return <main className="page-shell discovery-page"><section className="hero-panel"><span className="eyebrow">TAKE THE SCENIC ROUTE</span><h1 className="hero-title">A whole world<br />between the frames.</h1><p className="hero-copy">Follow a genre. Revisit a familiar universe. Find something you weren’t looking for.</p><div className="hero-actions"><Link className="cta-button" href="/movies">Explore every film <ArrowUpRight size={17}/></Link><Link className="text-action" href="/recommendations">Find a personal match <ArrowUpRight size={16}/></Link></div></section>
    {query.isPending && <LoadingState title="Opening new worlds" description="Finding the genres, collections and films in the catalog."/>}
    {query.isError && <ErrorState title="Discovery unavailable" description="The catalog couldn’t be reached. Your next discovery can wait a moment." onRetry={()=>void query.refetch()}/>}
    {dashboard && <><section className="home-chapter"><SectionHeading number="01" eyebrow="PICK A THREAD" title="There’s a world for that." description="Explore the genres represented in the catalog."/><div className="discovery-genre-grid">{dashboard.trending_by_genre.map(bucket=><Link className="discovery-genre-tile" key={bucket.label} href={`/genres/${encodeURIComponent(bucket.label)}`}><h3>{bucket.label}</h3><span className="meta">{bucket.movie_count} films to explore</span><ArrowUpRight size={19}/></Link>)}</div></section>
    {dashboard.trending_by_franchise.length>0 && <Reveal><section className="home-chapter"><SectionHeading number="02" eyebrow="SOME STORIES KEEP GOING" title="Back to a familiar universe."/><div className="franchise-paths">{dashboard.trending_by_franchise.map((bucket,i)=><Link href={`/franchises/${encodeURIComponent(bucket.label)}`} key={bucket.label}><span className="franchise-number">{String(i+1).padStart(2,'0')}</span><span><h3>{bucket.label}</h3><small>{bucket.movie_count} catalog titles</small></span><ArrowUpRight size={23}/></Link>)}</div></section></Reveal>}
    {collections.map(([label,items],i)=><Reveal key={label}><section className="home-chapter"><SectionHeading number={String(i+3).padStart(2,'0')} eyebrow="A DIFFERENT WAY IN" title={formatLabel(label)} description="A catalog collection arranged by stored attention scores, not human curation."/><div className="section-grid">{items.map(movie=><MovieCard key={movie.id} movie={movie}/>)}</div></section></Reveal>)}</>}
  </main>
}
