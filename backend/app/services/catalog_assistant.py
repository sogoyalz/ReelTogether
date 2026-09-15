"""Bounded, offline catalog retrieval with auditable, content-based ranking.

This is a focused rule-based assistant, not an LLM or a trained recommender.
Unknown metadata never satisfies a hard constraint. No provider calls on chat.
"""
import re
from datetime import date
from typing import get_args
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.movie import Movie
from app.services.provider_metadata import normalize_metadata
from app.schemas.assistant import ChatRequest, Filters, Genre, Language

LANGUAGE_CODES = dict(zip(get_args(Language), ["en", "hi", "ta", "te", "ml", "kn", "ko", "ja", "fr", "es"]))
ALIASES = {g: [g.lower()] for g in get_args(Genre)}
ALIASES.update({"Science Fiction": ["science fiction", "sci-fi", "sci fi", "scifi"], "Comedy": ["comedy", "comedies", "funny"], "Horror": ["horror", "scary"], "Romance": ["romance", "romantic"], "Animation": ["animation", "animated"]})


def parse_filters(message: str, previous: Filters):
    text = message.lower().strip()
    result = previous.model_copy(deep=True)
    recognized = False
    if re.search(r"\b(start over|reset|clear filters)\b", text):
        result = Filters()
        recognized = True
    positives, negatives = [], []
    # Negation scope continues through a list, but stops at a contrast or punctuation.
    for genre, aliases in ALIASES.items():
        for match in re.finditer(r"\b(?:" + "|".join(map(re.escape, aliases)) + r")\b", text):
            prefix = re.split(r"[.!?;]|\b(?:but|instead|however|i want|i'd like)\b", text[:match.start()])[-1]
            excluded = bool(re.search(r"\b(?:no|not|without|avoid|exclude|don't want)\b", prefix))
            (negatives if excluded else positives).append(genre)
            recognized = True
    if positives:
        result.genres = sorted(set(positives))
        result.excluded_genres = [g for g in result.excluded_genres if g not in positives]
    if negatives:
        result.excluded_genres = sorted(set(result.excluded_genres + negatives))
        result.genres = [g for g in result.genres if g not in negatives]
    if re.search(r"\bany genre\b", text):
        result.genres, result.excluded_genres = [], []
        recognized = True
    languages = [lang for lang in get_args(Language) if re.search(r"\b" + lang.lower() + r"\b", text)]
    if languages:
        # Unsupported language negation is clarified rather than inverted silently.
        if re.search(r"\b(?:no|not|without|avoid|exclude)\s+(?:" + "|".join(l.lower() for l in languages) + ")", text):
            return previous, False, "Choose the languages you do want in the filters; I don't yet understand language exclusions."
        result.languages = languages
        recognized = True
    if "any language" in text:
        result.languages = []
        recognized = True
    runtime = re.search(r"\b(under|less than|at most|up to|max(?:imum)?)\s+(\d+(?:\.\d+)?|one|two|three)\s*(minutes?|mins?|hours?|hrs?)\b", text)
    if runtime:
        word = runtime[2]
        amount = {"one": 1, "two": 2, "three": 3}.get(word)
        amount = amount if amount is not None else float(word)
        minutes = int(amount * (60 if runtime[3].startswith(("h", "hr")) else 1))
        if runtime[1] in {"under", "less than"}:
            minutes -= 1
        if not 1 <= minutes <= 600:
            return previous, False, "Please choose a runtime limit between 1 and 600 minutes."
        result.max_runtime = minutes
        recognized = True
    if re.search(r"\b(any length|any runtime|no runtime limit)\b", text):
        result.max_runtime = None
        recognized = True
    return result, recognized, None


def movie_runtime(movie: Movie):
    value = normalize_metadata(movie.provider_metadata).get("runtime")
    if isinstance(value, int) and not isinstance(value, bool):
        return value if value > 0 else None
    match = re.fullmatch(r"\s*(\d+)\s*(?:min(?:utes?)?)?\s*", str(value), re.I)
    return int(match[1]) if match and int(match[1]) > 0 else None


def movie_languages(movie: Movie):
    metadata = normalize_metadata(movie.provider_metadata)
    text = str(metadata.get("language") or "").lower()
    original = metadata.get("original_language")
    return [name for name, code in LANGUAGE_CODES.items() if original == code or re.search(r"\b" + name.lower() + r"\b", text)]


def recommend(db: Session, payload: ChatRequest, liked_ids=(), disliked_ids=(), watched_ids=()):
    filters, recognized, clarification = parse_filters(payload.message, payload.filters)
    if re.search(r"\b(?:netflix|hulu|streaming|prime video|available on|disney|rated above|rating above|after \d{4}|before \d{4}|from \d{4})\b", payload.message, re.I):
        clarification = "I can't reliably apply streaming, rating or year requests in chat yet. Use genres, languages and runtime here; streaming availability is not verified."
    # Only released titles can be a recommendation to watch. Never infer streaming availability.
    catalog = list(db.scalars(select(Movie).where(Movie.release_date <= date.today()).order_by(Movie.id)))
    by_id = {movie.id: movie for movie in catalog}
    seed_ids = set(liked_ids) | set(payload.favorite_ids)
    reference = re.search(r'\b(?:similar to|like)\s+["“]?(.+?)(?=\s+\b(?:but|under|less than|at most|up to|without)\b|,|$)', payload.message, re.I)
    if reference:
        title = reference[1].strip(' "“”.!?')
        matches = [movie for movie in catalog if movie.title.casefold() == title.casefold()]
        if len(matches) == 1:
            seed_ids.add(matches[0].id)
            # Parse constraints outside the reference, never genre words inside its title.
            remainder = payload.message[:reference.start()] + payload.message[reference.end():]
            filters, _, reference_error = parse_filters(remainder, payload.filters)
            clarification = clarification or reference_error
            recognized = True
        elif title.casefold() not in {alias for aliases in ALIASES.values() for alias in aliases}:
            clarification = "Pick that title in Favourite movies so I can use the exact movie, including its release year."
    seeds = [by_id[i] for i in sorted(seed_ids) if i in by_id]
    seeds = [m for m in seeds if m.id not in set(disliked_ids)]
    generic = bool(re.fullmatch(r"(?:please )?(?:recommend(?: movies| something| for me)?|find movies|show (?:me )?(?:movies|more)|more(?: please)?|surprise me|what should i watch|help|hi|hello)[.!?]*", payload.message.strip().lower()))
    if clarification or not (recognized or generic):
        return {"reply": clarification or "I can match genres, languages, runtime limits and favourite movies. Try ‘a thriller under two hours’, or use the filters. I don't yet understand that request well enough to change your recommendations.", "filters": payload.filters, "items": [], "total_matches": 0, "mode": "catalog-rules-v1", "needs_clarification": True}
    excluded = set(payload.excluded_ids) | seed_ids | set(disliked_ids) | set(watched_ids)
    ranked = []
    for movie in catalog:
        if movie.id in excluded:
            continue
        genres = set(movie.genres or [])
        if filters.genres and not genres.intersection(filters.genres):
            continue
        if genres.intersection(filters.excluded_genres):
            continue
        languages = movie_languages(movie)
        if filters.languages and not set(languages).intersection(filters.languages):
            continue
        runtime = movie_runtime(movie)
        if filters.max_runtime is not None and (runtime is None or runtime > filters.max_runtime):
            continue
        reasons = []
        overlaps = [(len(genres & set(seed.genres or [])) / max(1, len(genres | set(seed.genres or []))), seed) for seed in seeds]
        overlap, seed = max(overlaps, key=lambda row: row[0]) if overlaps else (0, None)
        if overlap and seed:
            shared = sorted(genres & set(seed.genres or []))
            reasons.append(f"Shares {', '.join(shared)} with {seed.title}.")
        if filters.genres:
            reasons.append(f"Matches your {', '.join(sorted(genres.intersection(filters.genres)))} preference.")
        if filters.languages:
            reasons.append(f"Catalog language: {', '.join(languages)}.")
        if filters.max_runtime is not None:
            reasons.append(f"Stored runtime: {runtime} minutes, within your {filters.max_runtime}-minute limit.")
        if not reasons:
            reasons.append("A discovery pick ordered by stored TMDB popularity; rate a few movies to personalize it.")
        # Similarity is the primary signal; stored popularity is only a tie-breaker.
        ranked.append((overlap, movie.tmdb_popularity or 0, movie.id, {"movie": {"id": movie.id, "slug": movie.slug, "poster_url": movie.poster_url, "title": movie.title, "release_date": movie.release_date, "genres": movie.genres, "runtime": runtime, "languages": languages}, "reasons": reasons}))
    ranked.sort(key=lambda row: (-row[0], -row[1], row[2]))
    items = [row[3] for row in ranked[:6]]
    reply = f"Here are {len(items)} picks from {len(ranked)} matching released movies."
    if not items:
        reply = "No more catalog movies match these constraints. Try removing a filter or starting over. Movies with unknown runtime or language are excluded when those filters are active."
    elif seeds:
        reply += " I used genre overlap with your favourites, then stored popularity to break ties."
    else:
        reply += " Pick a few favourites to make the ranking personal."
    return {"reply": reply, "filters": filters, "favorite_ids": sorted(set(payload.favorite_ids) | (seed_ids - set(liked_ids)))[:20], "items": items, "total_matches": len(ranked), "mode": "catalog-rules-v1", "needs_clarification": False}
