import Link from 'next/link'
import { ArrowUpRight } from 'lucide-react'

import type { MovieSummary } from '@/lib/api'
import { formatReleaseDate } from '@/lib/formatters'

export function MovieCard({ movie }: { movie: MovieSummary }) {
  const artwork = movie.poster_url || movie.backdrop_url
  const subtitle = movie.directors.length
    ? `Directed by ${movie.directors.slice(0, 2).join(', ')}`
    : movie.studios.length
      ? movie.studios.slice(0, 2).join(' • ')
      : 'Tracked title'

  return (
    <Link className="movie-card" href={`/movies/${movie.slug}`}>
      <div className="movie-card-media">
        {artwork ? (
          <img
            alt={movie.title}
            className="movie-poster"
            src={artwork}
          />
        ) : (
          <div className="movie-poster movie-poster-fallback">
            <span>{movie.title}</span>
          </div>
        )}
        <div className="movie-card-spotlight" />
        <div className="movie-card-hoverbar">
          <span>Open analysis</span>
          <ArrowUpRight size={16} />
        </div>
      </div>
      <div className="movie-card-body">
        <div className="title-row">
          <div>
            <h3>{movie.title}</h3>
            <p className="meta">{formatReleaseDate(movie.release_date)}</p>
            <p className="meta" style={{ marginTop: 6 }}>{subtitle}</p>
          </div>
          <div className="score-pill">{movie.hype_score}</div>
        </div>
        <div className="status-row">
          <span className={`status-badge status-${movie.status.toLowerCase()}`}>{movie.status}</span>
          <span className="meta">Buzz {movie.buzz_score}</span>
        </div>
        {movie.franchise ? (
          <div className="meta-line">
            <span className="meta-kicker">Franchise</span>
            <span>{movie.franchise}</span>
          </div>
        ) : null}
        <div className="meta-line">
          <span className="meta-kicker">Ratings</span>
          <span>{movie.imdb_rating ? `IMDb ${movie.imdb_rating}` : 'IMDb n/a'}</span>
          <span>{movie.rotten_tomatoes || 'RT n/a'}</span>
          <span>{movie.runtime || 'Runtime n/a'}</span>
        </div>
        <div className="genre-list">
          {movie.genres.map((genre) => (
            <span className="genre-tag" key={genre}>
              {genre}
            </span>
          ))}
        </div>
        <p className="subtle card-overview">{movie.overview || 'No overview available yet for this title.'}</p>
      </div>
    </Link>
  )
}
