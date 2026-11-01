"""SQLite and PostgreSQL catalog queries: hydrate only the requested page, never the full catalog.

JSON membership is exact; search remains literal substring matching. The two
small SQLite functions preserve Python's Unicode lowercase and rating parsing.
"""
from __future__ import annotations

import json
from datetime import date
from math import ceil

from sqlalchemy import Float, Numeric, String, case, cast, exists, false, func, literal, select, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.models.movie import Movie, MovieAnalytics
from app.repositories.movies import summary_analytics_option
from app.services.catalog_enrichment import CATALOG_ENRICHMENTS


def _enrichment(key: str, *, array: bool = True, postgres=False):
    fallback = case(
        {slug: json.dumps(data.get(key, [])) if array else data.get(key)
         for slug, data in CATALOG_ENRICHMENTS.items() if data.get(key)},
        value=Movie.slug,
        else_="[]" if array else None,
    )
    stored = (cast(Movie.enrichment_data[key], String) if array else Movie.enrichment_data[key].as_string()) if postgres else func.json_extract(Movie.enrichment_data, f"$.{key}")
    kind = func.jsonb_typeof(cast(Movie.enrichment_data[key], JSONB)) if postgres else func.json_type(Movie.enrichment_data, f"$.{key}")
    stored = case((kind == ("array" if array else ("string" if postgres else "text")), stored), else_=None)
    return func.coalesce(func.nullif(stored, "[]" if array else ""), fallback)


def _values(expression, postgres=False):
    if postgres:
        return func.jsonb_array_elements_text(cast(expression, JSONB)).table_valued("value", joins_implicitly=True).render_derived()
    return func.json_each(expression).table_valued("key", "value", joins_implicitly=True)


def _contains(expression, value, postgres=False):
    values = _values(expression, postgres)
    return exists(select(1).select_from(values).where(values.c.value == value))


def _words(expression, postgres=False):
    values = _values(expression, postgres)
    aggregate = func.string_agg(values.c.value, " ") if postgres else func.group_concat(values.c.value, " ")
    return select(func.coalesce(aggregate, "")).select_from(values).correlate(Movie).scalar_subquery()


def browse_sqlite(db: Session, filters):
    return browse_sql(db, filters)


def browse_sql(db: Session, filters):
    from app.services.catalog_browser import CatalogBrowseResult, _parse_rating

    # Register on the checked-out connection, including independently-created test engines.
    postgres = db.get_bind().dialect.name == "postgresql"
    lower = (lambda expression: func.lower(expression.collate("und-x-icu")).collate("C")) if postgres else func.catalog_lower
    if not postgres:
        connection = db.connection().connection.driver_connection
        connection.create_function("catalog_lower", 1, lambda value: (value or "").lower(), deterministic=True)
        connection.create_function("catalog_rating", 1, _parse_rating, deterministic=True)

    today = date.today()
    status = case((Movie.release_date <= today, "released"), (Movie.status == "announced", "announced"), else_="upcoming")
    year = cast(cast(func.extract("year", Movie.release_date), Numeric(4, 0)), String) if postgres else cast(func.strftime("%Y", Movie.release_date), String)
    fields = {key: _enrichment(key, postgres=postgres) for key in ("studios", "directors", "cast", "writers", "streaming_on")}
    franchise = _enrichment("franchise", array=False, postgres=postgres)
    # Pick one row deterministically even in legacy databases with duplicate latest labels.
    latest_id = select(func.max(MovieAnalytics.id)).where(
        MovieAnalytics.movie_id == Movie.id, MovieAnalytics.snapshot_label == "latest"
    ).correlate(Movie).scalar_subquery()
    source = Movie.__table__.outerjoin(MovieAnalytics, MovieAnalytics.id == latest_id)
    hype = func.coalesce(MovieAnalytics.hype_score, 0.0)
    buzz = func.coalesce(MovieAnalytics.buzz_score, 0.0)
    if postgres:
        raw_rating = func.trim(Movie.provider_metadata["imdb_rating"].as_string())
        valid = (func.length(raw_rating) <= 64) & raw_rating.op("~")(r"^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]{1,3})?$")
        number = case((valid, cast(raw_rating, Numeric)), else_=None)
        rating = case(((number <= 10) & (number >= cast(literal("2.4703282292062328e-324"), Numeric)), cast(number, Float)), else_=0.0)
    else:
        rating = func.catalog_rating(func.json_extract(Movie.provider_metadata, "$.imdb_rating"))
    title = lower(Movie.title)
    predicates = []
    if filters.query:
        text = Movie.title + literal(" ") + func.coalesce(Movie.overview, "") + literal(" ") + func.coalesce(franchise, "")
        for expression in (Movie.genres, fields["studios"], fields["cast"], fields["directors"], fields["writers"]):
            text = text + literal(" ") + _words(expression, postgres)
        # instr treats %, _ and backslashes literally, unlike LIKE.
        predicates.append((func.strpos(lower(text), filters.query.lower()) if postgres else func.instr(lower(text), filters.query.lower())) > 0)
    if filters.status:
        if filters.status == "released":
            predicates.append(Movie.release_date <= today)
        elif filters.status == "future":
            predicates.append(Movie.release_date > today)
        else:
            predicates.append(status == filters.status)
    if filters.genre:
        predicates.append(_contains(Movie.genres, filters.genre, postgres))
    for key, value in (("studios", filters.studio), ("directors", filters.director), ("streaming_on", filters.streaming)):
        if value:
            predicates.append(_contains(fields[key], value, postgres))
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
        .order_by(*ordering, (Movie.title.collate("C") if postgres else Movie.title).asc(), Movie.id.asc())
        .offset((page - 1) * filters.page_size).limit(filters.page_size)
        .options(summary_analytics_option())))

    # Facets describe the complete catalog, independent of active filters.
    facets = {}
    for key, expression in (("genres", Movie.genres), ("studios", fields["studios"]),
                            ("directors", fields["directors"]), ("streaming", fields["streaming_on"])):
        values = _values(expression, postgres)
        value = values.c.value.collate("C") if postgres else values.c.value
        facets[key] = list(db.scalars(select(value).select_from(Movie).join(values, true()).distinct().order_by(value)))
    if postgres: franchise = franchise.collate("C")
    facets["franchises"] = list(db.scalars(select(franchise).select_from(Movie).where(franchise.is_not(None), franchise != "").distinct().order_by(franchise)))
    facets["statuses"] = list(db.scalars(select(status).select_from(Movie).distinct().order_by(status)))
    facets["years"] = [int(value) for value in db.scalars(select(year).select_from(Movie).distinct().order_by(year.desc()))]
    return CatalogBrowseResult(movies, total, page, filters.page_size, total_pages, facets)
