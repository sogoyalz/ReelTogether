from app.services.provider_metadata import normalize_metadata
"""Fill only missing recommendation fields by verified TMDB ID, in bounded batches."""
from datetime import datetime, timezone
from sqlalchemy import select
from app.core.config import settings
from app.models.movie import Movie
from app.services.catalog_assistant import movie_runtime
from app.services.tmdb import _tmdb_get


def enrich_metadata(db, *, limit=25, after_id=0, apply=False):
    if not 1 <= limit <= 100 or after_id < 0:
        raise ValueError('Use limit 1..100 and after_id >= 0')
    if apply and not settings.tmdb_api_configured:
        raise ValueError('Set TMDB_API_KEY before applying enrichment')
    movies = list(db.scalars(select(Movie).where(Movie.id > after_id).order_by(Movie.id)))
    candidates = [m for m in movies if movie_runtime(m) is None or not (normalize_metadata(m.provider_metadata).get('original_language') or normalize_metadata(m.provider_metadata).get('language'))]
    selected = candidates[:limit]
    report = {'apply': apply, 'pending_after_cursor': len(candidates), 'selected_ids': [m.id for m in selected], 'updated': 0, 'failures': [], 'last_processed_id': after_id, 'stopped_early': False}
    if not apply:
        return report
    failures = 0
    for movie in selected:
        try:
            details = _tmdb_get(f'movie/{movie.tmdb_id}')
            if not isinstance(details, dict) or details.get('id') != movie.tmdb_id:
                raise ValueError('Identity mismatch')
            metadata = normalize_metadata(movie.provider_metadata)
            changed = []
            runtime = details.get('runtime')
            if movie_runtime(movie) is None and isinstance(runtime, int) and not isinstance(runtime, bool) and 1 <= runtime <= 600:
                metadata['runtime'] = f'{runtime} min'
                changed.append('runtime')
            language = details.get('original_language')
            if not metadata.get('original_language') and isinstance(language, str) and len(language) == 2 and language.isalpha():
                metadata['original_language'] = language.lower()
                changed.append('original_language')
            if changed:
                metadata['recommendation_enrichment'] = {'source': 'tmdb', 'source_url': f'https://www.themoviedb.org/movie/{movie.tmdb_id}', 'verified_at': datetime.now(timezone.utc).isoformat(), 'fields': changed}
                movie.provider_metadata = metadata
                db.commit()
                report['updated'] += 1
            failures = 0
        except (RuntimeError, ValueError, OSError):
            db.rollback()
            report['failures'].append({'movie_id': movie.id, 'error': 'provider_fetch_or_identity_failed'})
            failures += 1
        report['last_processed_id'] = movie.id
        if failures >= 3:
            report['stopped_early'] = True
            break
    return report
