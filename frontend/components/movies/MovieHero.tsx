import Link from 'next/link'
import { ArrowUpRight, Star, Users } from 'lucide-react'
import { WatchlistButton } from './WatchlistButton'
import { MovieArtwork } from '@/components/shared/MovieArtwork'
import type { MovieDetail } from '@/lib/api'
import { formatReleaseDate } from '@/lib/formatters'

export function MovieHero({ movie }: { movie: MovieDetail }) {
  return (
    <section className="cinema-detail-hero" aria-labelledby="movie-title">
      <MovieArtwork src={movie.backdrop_url || movie.poster_url} title={movie.title} backdrop />
      <div className="cinema-detail-poster"><MovieArtwork src={movie.poster_url} title={movie.title} /></div>
      <div className="cinema-detail-copy">
        <span className="cinema-kicker">{movie.status === 'released' ? 'NOW IN THE LIBRARY' : 'ON THE HORIZON'}</span>
        <h1 id="movie-title">{movie.title}</h1>
        <p className="cinema-detail-meta">{formatReleaseDate(movie.release_date)}{movie.runtime ? ` · ${movie.runtime}` : ''}</p>
        <div className="cinema-genre-links">{movie.genres.map(genre => <Link href={`/genres/${encodeURIComponent(genre)}`} key={genre}>{genre}</Link>)}
          {movie.imdb_rating && <span className="cinema-rating"><Star size={14} aria-hidden="true" /> {movie.imdb_rating} <small>IMDb</small></span>}
        </div>
        <p className="cinema-synopsis">{movie.overview || 'A synopsis is not available for this film yet.'}</p>
        <div className="cinema-detail-actions"><WatchlistButton movieId={movie.id} /><Link className="cta-button secondary-button" href="/movie-night"><Users size={16} /> Plan a movie night</Link></div>
        {movie.franchise && <Link className="cinema-collection-link" href={`/franchises/${encodeURIComponent(movie.franchise)}`}>Explore {movie.franchise} <ArrowUpRight size={14} /></Link>}
      </div>
    </section>
  )
}
