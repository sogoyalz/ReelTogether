from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import urlopen

from app.services.cache import ExpiringMap
from app.models.movie import Movie

WIKIDATA_SEARCH_URL = "https://www.wikidata.org/w/api.php"
WIKIDATA_ENTITY_URL = "https://www.wikidata.org/wiki/Special:EntityData"
WIKIDATA_PAGE_URL = "https://www.wikidata.org/wiki"
_CACHE = ExpiringMap()


def fetch_movie_wikidata(movie: Movie) -> dict[str, str | list[str] | None] | None:
    cache_key = f"{movie.title}:{movie.release_date.year}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    candidates = [
        f"{movie.title} {movie.release_date.year} film",
        f"{movie.title} film",
        movie.title,
    ]

    for candidate in candidates:
        entity_id = _search_entity(candidate)
        if not entity_id:
            continue
        entity = _fetch_entity(entity_id)
        if entity is None:
            continue

        claims = entity.get("claims", {})
        metadata = {
            "id": entity_id,
            "url": f"{WIKIDATA_PAGE_URL}/{quote(entity_id)}",
            "label": _localized_value(entity.get("labels", {})),
            "description": _localized_value(entity.get("descriptions", {})),
            "instance_of": _claim_labels(claims.get("P31", [])),
            "genres": _claim_labels(claims.get("P136", [])),
            "countries": _claim_labels(claims.get("P495", [])),
        }
        _CACHE[cache_key] = metadata
        return metadata

    _CACHE[cache_key] = None
    return None


def _search_entity(query: str) -> str | None:
    params = urlencode(
        {
            "action": "wbsearchentities",
            "format": "json",
            "language": "en",
            "type": "item",
            "limit": 1,
            "search": query,
        }
    )
    try:
        with urlopen(f"{WIKIDATA_SEARCH_URL}?{params}", timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError):
        return None

    search = payload.get("search", [])
    if not search:
        return None
    entity_id = search[0].get("id")
    return entity_id if isinstance(entity_id, str) else None


def _fetch_entity(entity_id: str) -> dict | None:
    try:
        with urlopen(f"{WIKIDATA_ENTITY_URL}/{quote(entity_id)}.json", timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError):
        return None
    entity = payload.get("entities", {}).get(entity_id)
    return entity if isinstance(entity, dict) else None


def _localized_value(payload: dict) -> str | None:
    value = payload.get("en", {}).get("value")
    return value if isinstance(value, str) and value.strip() else None


def _claim_labels(claims: list[dict]) -> list[str]:
    entity_ids: list[str] = []
    for claim in claims[:4]:
        mainsnak = claim.get("mainsnak", {})
        datavalue = mainsnak.get("datavalue", {})
        value = datavalue.get("value", {})
        if isinstance(value, dict):
            entity_id = value.get("id")
            if isinstance(entity_id, str):
                entity_ids.append(entity_id)
    return _resolve_entity_labels(entity_ids)


def _resolve_entity_labels(entity_ids: list[str]) -> list[str]:
    if not entity_ids:
        return []

    params = urlencode(
        {
            "action": "wbgetentities",
            "format": "json",
            "languages": "en",
            "props": "labels",
            "ids": "|".join(entity_ids),
        }
    )
    try:
        with urlopen(f"{WIKIDATA_SEARCH_URL}?{params}", timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError):
        return entity_ids

    entities = payload.get("entities", {})
    labels: list[str] = []
    for entity_id in entity_ids:
        label = entities.get(entity_id, {}).get("labels", {}).get("en", {}).get("value")
        labels.append(label if isinstance(label, str) and label.strip() else entity_id)
    return labels
