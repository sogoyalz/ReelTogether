from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from app.core.config import settings
from app.services.cache import ExpiringMap
from app.models.movie import Movie
from app.services.provider_metadata import normalize_metadata, metadata_text

OMDB_API_ENDPOINT = "https://www.omdbapi.com/"
_CACHE = ExpiringMap()


def fetch_movie_metadata(movie: Movie) -> dict[str, str | None] | None:
    if not settings.omdb_api_configured:
        return normalize_metadata(movie.provider_metadata) or None

    cache_key = (movie.title, movie.release_date.year)
    if cache_key in _CACHE:
        return _CACHE[cache_key] or normalize_metadata(movie.provider_metadata) or None

    params = {
        "apikey": settings.OMDB_API_KEY,
        "t": movie.title,
        "y": movie.release_date.year,
        "type": "movie",
        "plot": "short",
        "tomatoes": "true",
    }

    try:
        with urlopen(f"{OMDB_API_ENDPOINT}?{urlencode(params)}", timeout=4) as response:

            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError):
        _CACHE[cache_key] = None
        return normalize_metadata(movie.provider_metadata) or None

    if not isinstance(payload, dict) or payload.get("Response") != "True":
        _CACHE[cache_key] = None
        return normalize_metadata(movie.provider_metadata) or None

    entries = payload.get("Ratings")
    ratings = {rating["Source"]: rating.get("Value") for rating in (entries if isinstance(entries, list) else []) if isinstance(rating, dict) and isinstance(rating.get("Source"), str)}
    metadata = {
        "imdb_id": _normalize_str(payload.get("imdbID")),
        "rated": _normalize_str(payload.get("Rated")),
        "runtime": _normalize_str(payload.get("Runtime")),
        "language": _normalize_str(payload.get("Language")),
        "box_office": _normalize_str(payload.get("BoxOffice")),
        "awards": _normalize_str(payload.get("Awards")),
        "metascore": _normalize_str(payload.get("Metascore")),
        "imdb_rating": _normalize_str(payload.get("imdbRating")),
        "imdb_votes": _normalize_str(payload.get("imdbVotes")),
        "rotten_tomatoes": _normalize_str(ratings.get("Rotten Tomatoes")),
        "omdb_poster_url": _normalize_str(payload.get("Poster")),
    }
    _CACHE[cache_key] = metadata
    return metadata


def _normalize_str(value: Any) -> str | None:
    return metadata_text(value)
