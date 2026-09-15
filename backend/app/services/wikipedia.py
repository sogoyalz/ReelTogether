from __future__ import annotations

from urllib.parse import quote

import wikipediaapi

from app.services.cache import ExpiringMap
from app.models.movie import Movie

WIKIPEDIA_BASE_URL = "https://en.wikipedia.org/wiki/"
_CACHE = ExpiringMap()

_wiki = wikipediaapi.Wikipedia(
    user_agent="ReelTogether/1.0 (https://github.com/sogoyalz/ReelTogether)",
    language="en",
    timeout=4,
)


def fetch_movie_wikipedia(movie: Movie) -> dict[str, str | list[str] | None] | None:
    cache_key = f"{movie.title}:{movie.release_date.year}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    candidates = [
        f"{movie.title} ({movie.release_date.year} film)",
        f"{movie.title} (film)",
        movie.title,
    ]

    for candidate in candidates:
        try:
            page = _wiki.page(candidate)
            if not page.exists():
                continue
            metadata = {
                "title": page.title, "summary": _clean_summary(page.summary),
                "url": page.fullurl or f"{WIKIPEDIA_BASE_URL}{quote(page.title.replace(' ', '_'))}",
                "categories": _top_categories(page),
            }
        except Exception:
            continue
        _CACHE[cache_key] = metadata
        return metadata

    _CACHE[cache_key] = None
    return None


def _clean_summary(summary: str | None) -> str | None:
    if not summary:
        return None
    cleaned = " ".join(summary.split())
    if not cleaned:
        return None
    return cleaned[:560].rstrip()


def _top_categories(page: wikipediaapi.WikipediaPage) -> list[str]:
    categories = []
    for category in page.categories.keys():
        label = category.replace("Category:", "")
        if "articles" in label.lower():
            continue
        categories.append(label)
        if len(categories) == 4:
            break
    return categories
