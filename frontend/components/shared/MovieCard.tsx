import Link from 'next/link'
import type { MovieSummary } from '@/lib/api'
import { MovieArtwork } from './MovieArtwork'

export function MovieCard({ movie }: { movie: MovieSummary }) {
  return <Link className="movie-card film-card" href={`/movies/${movie.slug}`}>
    <div className="film-card-image"><MovieArtwork src={movie.poster_url} title={movie.title} /><span className="film-card-open">Explore movie ↗</span></div>
    <div className="movie-card-body">
      <div className="film-card-meta"><span>{movie.release_date.slice(0, 4)}</span><span>{movie.imdb_rating ? `IMDb ${movie.imdb_rating}` : movie.status === 'released' ? 'Released' : 'Coming soon'}</span></div>
      <h3>{movie.title}</h3>
      <p className="meta">{movie.genres.slice(0, 2).join(' · ') || 'Explore this title'}</p>
    </div>
  </Link>
}
