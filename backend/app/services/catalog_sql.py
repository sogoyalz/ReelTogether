"""SQLite catalog queries: hydrate only the requested page, never the full catalog.

JSON membership is exact; search remains literal substring matching. The two
small SQLite functions preserve Python's Unicode lowercase and rating parsing.
"""
from __future__ import annotations

import json
from datetime import date
from math import ceil

from sqlalchemy import String, case, cast, exists, false, func, literal, select, true
from sqlalchemy.orm import Session

from app.models.movie import Movie, MovieAnalytics
from app.repositories.movies import summary_analytics_option
from app.services.catalog_enrichment import CATALOG_ENRICHMENTS


def _enrichment(key: str, *, array: bool = True):
    fallback = case(
        {slug: json.dumps(data.get(key, [])) if array else data.get(key)
         for slug, data in CATALOG_ENRICHMENTS.items() if data.get(key)},
        value=Movie.slug,
        else_="[]" if array else None,
    )
    stored = func.json_extract(Movie.enrichment_data, f"$.{key}")
    return func.coalesce(func.nullif(stored, "[]" if array else ""), fallback)


def _values(expression):
    return func.json_each(expression).table_valued("key", "value", joins_implicitly=True)


def _contains(expression, value):
    values = _values(expression)
    return exists(select(1).select_from(values).where(values.c.value == value))


def _words(expression):
    values = _values(expression)
    return select(func.coalesce(func.group_concat(values.c.value, " "), "")).select_from(values).correlate(Movie).scalar_subquery()


def browse_sqlite(db: Session, filters):
    from app.services.catalog_browser import CatalogBrowseResult, _parse_rating

    # Register on the checked-out connection, including independently-created test engines.
    connection = db.connection().connection.driver_connection
    connection.create_function("catalog_lower", 1, lambda value: (value or "").lower(), deterministic=True)
    connection.create_function("catalog_rating", 1, _parse_rating, deterministic=True)

    today = date.today()
    status = case((Movie.release_date <= today, "released"), (Movie.status == "announced", "announced"), else_="upcoming")
    year = cast(func.strftime("%Y", Movie.release_date), String)
    fields = {key: _enrichment(key) for key in ("studios", "directors", "cast", "writers", "streaming_on")}
    franchise = _enrichment("franchise", array=False)
    # Pick one row deterministically even in legacy databases with duplicate latest labels.
    latest_id = select(func.max(MovieAnalytics.id)).where(
        MovieAnalytics.movie_id == Movie.id, MovieAnalytics.snapshot_label == "latest"
    ).correlate(Movie).scalar_subquery()
    source = Movie.__table__.outerjoin(MovieAnalytics, MovieAnalytics.id == latest_id)
    hype = func.coalesce(MovieAnalytics.hype_score, 0.0)
    buzz = func.coalesce(MovieAnalytics.buzz_score, 0.0)
    rating = func.catalog_rating(func.json_extract(Movie.provider_metadata, "$.imdb_rating"))
    title = func.catalog_lower(Movie.title)
    predicates = []
    if filters.query:
        text = Movie.title + literal(" ") + func.coalesce(Movie.overview, "") + literal(" ") + func.coalesce(franchise, "")
        for expression in (Movie.genres, fields["studios"], fields["cast"], fields["directors"], fields["writers"]):
            text = text + literal(" ") + _words(expression)
        # instr treats %, _ and backslashes literally, unlike LIKE.
        predicates.append(func.instr(func.catalog_lower(text), filters.query.lower()) > 0)
    if filters.status:
        if filters.status == "released":
            predicates.append(Movie.release_date <= today)
        elif filters.status == "future":
            predicates.append(Movie.release_date > today)
        else:
            predicates.append(status == filters.status)
    if filters.genre:
        predicates.append(_contains(Movie.genres, filters.genre))
    for key, value in (("studios", filters.studio), ("directors", filters.director), ("streaming_on", filters.streaming)):
        if value:
            predicates.append(_contains(fields[key], value))
    if filters.franchise:
        predicates.append(franchise == filters.franchise)
    if filters.year:
        # Range predicates can use the existing release-date index.
        if 1 <= filters.year <= 9999:
            predicates.extend((Movie.release_date >= date(filters.year, 1, 1), Movie.release_date <= date(filters.year, 12, 31)))
        else:
            predicates.append(false())
    for minimum, expression in ((filters.min_rating, rating), (filters.min_hype, hype), (filters.min_popularity, Movie.tmdb_popularity)):
        if minimum:
            predicates.append(expression >= minimum)

    total = db.scalar(select(func.count()).select_from(source).where(*predicates)) or 0
    total_pages = max(1, ceil(total / filters.page_size))
    page = min(max(1, filters.page), total_pages)
    sorters = {
        "rating": (rating.desc(), hype.desc(), title.desc()),
        "popularity": (Movie.tmdb_popularity.desc(), hype.desc(), title.desc()),
        "release": (Movie.release_date.desc(), hype.desc(), title.desc()),
        "buzz": (buzz.desc(), hype.desc(), title.desc()),
        "hype": (hype.desc(), Movie.tmdb_popularity.desc(), title.desc()),
        "title": (title.asc(),),
        "release_asc": (Movie.release_date.asc(), Movie.id.asc()),
        "none": (Movie.id.asc(),),
    }
    ordering = sorters.get(filters.sort, sorters["hype"])
    movies = list(db.scalars(select(Movie).select_from(source).where(*predicates)
        .order_by(*ordering, Movie.title.asc(), Movie.id.asc())
        .offset((page - 1) * filters.page_size).limit(filters.page_size)
        .options(summary_analytics_option())))

    # Facets describe the complete catalog, independent of active filters.
    facets = {}
    for key, expression in (("genres", Movie.genres), ("studios", fields["studios"]),
                            ("directors", fields["directors"]), ("streaming", fields["streaming_on"])):
        values = _values(expression)
        facets[key] = list(db.scalars(select(values.c.value).select_from(Movie).join(values, true()).distinct().order_by(values.c.value)))
    facets["franchises"] = list(db.scalars(select(franchise).select_from(Movie).where(franchise.is_not(None), franchise != "").distinct().order_by(franchise)))
    facets["statuses"] = list(db.scalars(select(status).select_from(Movie).distinct().order_by(status)))
    facets["years"] = [int(value) for value in db.scalars(select(year).select_from(Movie).distinct().order_by(year.desc()))]
    return CatalogBrowseResult(movies, total, page, filters.page_size, total_pages, facets)
